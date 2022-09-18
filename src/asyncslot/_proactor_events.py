""" _proactor_events.py - implements proactor event loop (for Windows) """


import sys

if sys.platform != 'win32':
    raise ImportError('win32 only')

import _overlapped
import _winapi
import asyncio
import concurrent.futures
import math
import threading
import weakref
from typing import Optional
from ._base_events import *


__all__ = 'AsyncSlotProactorEventLoop', 'AsyncSlotProactorEventLoopPolicy',


class AsyncSlotProactor(asyncio.IocpProactor):
    def __init__(
        self, write_to_self: weakref.WeakMethod, concurrency=0xffffffff,
    ):
        super().__init__(concurrency)

        self.__write_to_self = write_to_self
        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.__dequeue_future: Optional[concurrent.futures.Future] = None
        self.__idle = threading.Event()
        self.__idle.set()

        # Completion messages are posted to __poll_iocp
        self.__poll_iocp = _overlapped.CreateIoCompletionPort(
            _overlapped.INVALID_HANDLE_VALUE, 0, 0, concurrency)

        self.__notifier: Optional[AsyncSlotNotifier] = None

    def __wake_up(self):
        self._check_closed()
        if not self.__idle.is_set():
            write_to_self = self.__write_to_self()
            assert write_to_self is not None, (
                'AsyncSlotEventLoop is supposed to close AsyncSlotProactor '
                'before being deleted')
            write_to_self()
            self.__idle.wait()

    def set_notifier(self, notifier: Optional[AsyncSlotNotifier]) -> None:
        self.__wake_up()
        self.__notifier = notifier

    def _poll(self, timeout=None):
        self._check_closed()

        # _poll is called by super().select() and super().close().
        #
        # If the last call to select() raised AsyncSlotYield, the caller
        # (from _run_once) should only call select() again after receiving
        # a notification from us, and we only send a notification after
        # entering IDLE state.
        #
        # If called from close(), we also require the proactor to have
        # been woken up (by a call to set_notifier) before closing.
        assert self.__idle.is_set(), 'unexpected _poll'

        # If any (zero or more) IO events have been copied from _iocp to
        # __poll_iocp, perform _poll from __poll_iocp.
        if self.__dequeue_future is not None:
            real_iocp = self._iocp
            try:
                self._iocp = self.__poll_iocp
                # TODO: we assume super()._poll() exhaust the events in
                # TODO: __poll_iocp.  If not, this is a logic error.
                return super()._poll(0)
            finally:
                self._iocp = real_iocp
                self.__dequeue_future = None

        # Perform normal (blocking) polling if no notifier is set.
        # In particular, this is the case when called by close().
        if self.__notifier is None:
            return super()._poll(timeout)

        # Perform normal polling if timeout is zero.
        if timeout is not None and timeout <= 0:
            return super()._poll(timeout)

        # Convert timeout to milliseconds (same as super()._poll()).
        if timeout is None:
            ms = 0xffffffff
        else:
            ms = math.ceil(timeout * 1e3)
            if ms >= 0xffffffff:
                raise ValueError("timeout too big")

        # Launch a thread worker to wait for IO on self._iocp and copy it
        # to self.__poll_iocp.
        self.__idle.clear()
        try:
            self.__dequeue_future = self.__executor.submit(self.__dequeue, ms)
        except BaseException:
            # Should submit() raise, we assume no task is spawned.
            self.__idle.set()
            raise
        raise AsyncSlotYield

    def __dequeue(self, ms: int):
        """ Dequeue all available messages from self._iocp and copy them to
        self.__poll_iocp.  If no message is available, block for at most ms
        milliseconds. """

        # Source code of _overlapped.GetQueuedCompletionStatus:
        # https://github.com/python/cpython/blob/f07adf82f338ebb7e69475537be050e63c2009fa/Modules/clinic/overlapped.c.h#L76
        # https://github.com/python/cpython/blob/858c9a58bf56cefc792bf0eb1ba22984b7b2d150/Modules/overlapped.c#L256

        # Source code of _overlapped.PostQueuedCompletionStatus:
        # https://github.com/python/cpython/blob/f07adf82f338ebb7e69475537be050e63c2009fa/Modules/clinic/overlapped.c.h#L108
        # https://github.com/python/cpython/blob/858c9a58bf56cefc792bf0eb1ba22984b7b2d150/Modules/overlapped.c#L296

        notifier = self.__notifier
        try:
            # Note: any exception raised is propagated to the main thread
            # the next time select() is called, and will bring down the
            # AsyncSlotEventLoop.
            while True:
                # --- BEGIN COPIED FROM IocpProactor._poll
                status = _overlapped.GetQueuedCompletionStatus(self._iocp, ms)
                if status is None:
                    break
                ms = 0
                # --- END COPIED FROM IocpProactor._poll

                err, transferred, key, address = status  # err is not used
                _overlapped.PostQueuedCompletionStatus(
                    self.__poll_iocp, transferred, key, address)
        finally:
            self.__idle.set()
            notifier.notify()

    def close(self):
        assert self.__idle.is_set(), 'unexpected close'
        assert self.__notifier is None, 'notifier must have been reset'

        # Note: super().close() calls self._poll() repeatedly to exhaust
        # IO events.  The first call might be served by __poll_iocp; the
        # remaining calls are guaranteed to block because __notifier is
        # None.
        super().close()

        if self.__poll_iocp is not None:
            self.__dequeue_future = None
            self.__executor.shutdown()
            _winapi.CloseHandle(self.__poll_iocp)
            self.__poll_iocp = None


class AsyncSlotProactorEventLoop(AsyncSlotBaseEventLoop,
                                 asyncio.ProactorEventLoop):
    def __init__(self, *, standalone=True):
        proactor = AsyncSlotProactor(weakref.WeakMethod(self._write_to_self))
        super().__init__(proactor, standalone=standalone)

    def _asyncslot_loop_startup(self):
        # ---- BEGIN COPIED FROM ProactorEventLoop.run_forever
        assert self._self_reading_future is None
        self.call_soon(self._loop_self_reading)
        # ---- END COPIED FROM ProactorEventLoop.run_forever
        super()._asyncslot_loop_startup()

    def _asyncslot_loop_cleanup(self):
        super()._asyncslot_loop_cleanup()
        # ---- BEGIN COPIED FROM ProactorEventLoop.run_forever
        if self._self_reading_future is not None:
            ov = self._self_reading_future._ov
            self._self_reading_future.cancel()
            # self_reading_future was just cancelled so if it hasn't been
            # finished yet, it never will be (it's possible that it has
            # already finished and its callback is waiting in the queue,
            # where it could still happen if the event loop is restarted).
            # Unregister it otherwise IocpProactor.close will wait for it
            # forever
            if ov is not None:
                self._proactor._unregister(ov)
            self._self_reading_future = None
        # ---- END COPIED FROM ProactorEventLoop.run_forever


class AsyncSlotProactorEventLoopPolicy(asyncio.events.BaseDefaultEventLoopPolicy):
    _loop_factory = AsyncSlotProactorEventLoop

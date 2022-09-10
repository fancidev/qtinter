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
from typing import Optional
from ._base_events import *


__all__ = 'AsyncSlotProactorEventLoop', 'AsyncSlotProactorEventLoopPolicy',


class AsyncSlotProactor(asyncio.IocpProactor):
    def __init__(self, concurrency = 0xffffffff):
        super().__init__(concurrency)

        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.__dequeue_future: Optional[concurrent.futures.Future] = None
        self.__dequeue_done = threading.Event()

        # Completion messages are posted to __poll_iocp
        self.__poll_iocp = _overlapped.CreateIoCompletionPort(
            _overlapped.INVALID_HANDLE_VALUE, 0, 0, concurrency)

        self.__notifier: Optional[AsyncSlotNotifier] = None

    def set_notifier(self, notifier: Optional[AsyncSlotNotifier]) -> None:
        # self._unblock_if_blocked()
        self.__notifier = notifier

    def select(self, timeout=None):

        if self.__dequeue_future is not None:
            assert self.__dequeue_done.is_set(), 'unexpected select'
            real_iocp = self._iocp
            try:
                return super().select(0)
            finally:
                self._iocp = real_iocp
                self.__dequeue_done.clear()
                self.__dequeue_future = None

        if timeout is not None and timeout <= 0:
            return super().select(timeout)

        if timeout is None:
            ms = 0xffffffff
        else:
            ms = math.ceil(timeout * 1e3)
            if ms >= 0xffffffff:
                raise ValueError("timeout too big")

        assert self.__notifier is not None, 'missing set_notifier'
        self.__dequeue_future = self.__executor.submit(self.__dequeue, ms)
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

        while True:
            # TODO: handle exception raised by GetQueuedCompletionStatus

            # --- BEGIN COPIED FROM IocpProactor._poll
            status = _overlapped.GetQueuedCompletionStatus(self._iocp, ms)
            if status is None:
                break
            ms = 0
            # --- END COPIED FROM IocpProactor._poll

            err, transferred, key, address = status  # err is not used
            if address == 1:  # magic number used to wake up the worker
                return
            _overlapped.PostQueuedCompletionStatus(
                self.__poll_iocp, transferred, key, address)

        self.__dequeue_done.set()
        self.__notifier.notify()

    def close(self):
        if self.__poll_iocp is not None:
            if (self.__dequeue_future is not None and
                    not self.__dequeue_done.set()):
                # Post a special message with Overlapped = 1 to unblock the
                # worker.  _overlapped.GetQueuedCompletionStatus raises an
                # exception if it gets Overlapped == 0.
                # TODO: handle error from PostQueuedCompletionStatus
                _overlapped.PostQueuedCompletionStatus(self._iocp, 0, 0, 1)
                try:
                    self.__dequeue_future.result()  # waits
                except Exception as exc:
                    # TODO: check exception type
                    print(repr(exc))
                    pass
            self.__dequeue_done = None
            self.__dequeue_future = None
            _winapi.CloseHandle(self.__poll_iocp)
            self.__poll_iocp = None
        super().close()


class AsyncSlotProactorEventLoop(AsyncSlotBaseEventLoop,
                                 asyncio.ProactorEventLoop):
    def __init__(self):
        proactor = AsyncSlotProactor()
        super().__init__(proactor)

    def __enter__(self):
        # ---- BEGIN COPIED FROM ProactorEventLoop.run_forever
        assert self._self_reading_future is None
        self.call_soon(self._loop_self_reading)
        # ---- END COPIED FROM ProactorEventLoop.run_forever
        super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
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

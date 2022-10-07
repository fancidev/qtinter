""" _windows_events.py - implements proactor event loop under Windows """

import sys

if sys.platform != 'win32':
    raise ImportError('win32 only')

import _overlapped
import _winapi
import asyncio.windows_events
import concurrent.futures
import math
import sys
import threading
from typing import Optional
from ._selectable import _QiNotifier
from . import _proactor_events
from . import _selector_events


__all__ = (
    'QiDefaultEventLoop',
    'QiDefaultEventLoopPolicy',
    'QiProactorEventLoop',
    'QiProactorEventLoopPolicy',
    'QiSelectorEventLoop',
    'QiSelectorEventLoopPolicy',
)


INFINITE = 0xffffffff


class _QiProactor(asyncio.IocpProactor):
    def __init__(self, concurrency=0xffffffff):
        super().__init__(concurrency)

        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.__dequeue_future: Optional[concurrent.futures.Future] = None
        self.__idle = threading.Event()
        self.__idle.set()
        self.__notifier: Optional[_QiNotifier] = None

    def __wakeup(self):
        self._check_closed()
        if not self.__idle.is_set():
            assert self.__notifier is not None, 'notifier expected'
            self.__notifier.wakeup()
            self.__idle.wait()

    def set_notifier(self, notifier: Optional[_QiNotifier]) -> None:
        self.__wakeup()
        self.__notifier = notifier

    def _poll(self, timeout=None):
        # _poll is called by super().select() and super().close().
        #
        # If the last call to select() raised QiYield, the caller
        # (from _run_once) should only call select() again after receiving
        # a notification from us, and we only send a notification after
        # entering IDLE state.
        #
        # If called from close(), we also require the proactor to have
        # been woken up (by a call to set_notifier) before closing.
        #
        # The code below is copied verbatim from asyncio.windows_events,
        # except that _overlapped is 'redirected' to this object's
        # non-blocking implementation.  The code is unchanged from Python
        # 3.7 through Python 3.11.
        _overlapped = self

        # --- BEGIN COPIED FROM asyncio.windows_events.IocpProactor._poll
        if timeout is None:
            ms = INFINITE
        elif timeout < 0:
            raise ValueError("negative timeout")
        else:
            # GetQueuedCompletionStatus() has a resolution of 1 millisecond,
            # round away from zero to wait *at least* timeout seconds.
            ms = math.ceil(timeout * 1e3)
            if ms >= INFINITE:
                raise ValueError("timeout too big")

        while True:
            status = _overlapped.GetQueuedCompletionStatus(self._iocp, ms)
            if status is None:
                break
            ms = 0

            err, transferred, key, address = status
            try:
                f, ov, obj, callback = self._cache.pop(address)
            except KeyError:
                if self._loop.get_debug():
                    self._loop.call_exception_handler({
                        'message': ('GetQueuedCompletionStatus() returned an '
                                    'unexpected event'),
                        'status': ('err=%s transferred=%s key=%#x address=%#x'
                                   % (err, transferred, key, address)),
                    })

                # key is either zero, or it is used to return a pipe
                # handle which should be closed to avoid a leak.
                if key not in (0, _overlapped.INVALID_HANDLE_VALUE):
                    _winapi.CloseHandle(key)
                continue

            if obj in self._stopped_serving:
                f.cancel()
            # Don't call the callback if _register() already read the result or
            # if the overlapped has been cancelled
            elif not f.done():
                try:
                    value = callback(transferred, key, ov)
                except OSError as e:
                    f.set_exception(e)
                    self._results.append(f)
                else:
                    f.set_result(value)
                    self._results.append(f)

        # Remove unregistered futures
        for ov in self._unregistered:
            self._cache.pop(ov.address, None)
        self._unregistered.clear()
        # --- END COPIED FROM asyncio.windows_events.IocpProactor._poll

    def GetQueuedCompletionStatus(self, iocp, ms):
        assert iocp is self._iocp

        assert self.__idle.is_set(), 'unexpected _poll'

        # If any prior dequeue result is available, return that.
        if self.__dequeue_future is not None:
            try:
                return self.__dequeue_future.result()
            finally:
                self.__dequeue_future = None

        # Perform normal (blocking) polling if no notifier is set.
        # In particular, this is the case when called by close().
        if self.__notifier is None:
            return _overlapped.GetQueuedCompletionStatus(self._iocp, ms)

        # Perform normal polling if timeout is zero.
        if ms == 0:
            return _overlapped.GetQueuedCompletionStatus(self._iocp, ms)

        # Try non-blocking dequeue and return if any result is available.
        status = _overlapped.GetQueuedCompletionStatus(self._iocp, 0)
        if status is not None:
            return status

        # Launch a thread worker to wait for IO.
        self.__idle.clear()
        try:
            self.__dequeue_future = self.__executor.submit(self.__dequeue, ms)
        except BaseException:
            # Should submit() raise, we assume no task is spawned.
            self.__idle.set()
            raise
        else:
            return self.__notifier.no_result()  # raises _QiYield

    def __dequeue(self, ms: int):
        try:
            # Note: any exception raised is propagated to the main thread
            # the next time select() is called, and will bring down the
            # QiEventLoop.
            return _overlapped.GetQueuedCompletionStatus(self._iocp, ms)
        finally:
            # Make a copy of self.__notifier because it may be altered by
            # set_notifier immediately after self.__idle is set.
            notifier = self.__notifier
            self.__idle.set()
            notifier.notify()

    def close(self):
        assert self.__idle.is_set(), 'unexpected close'
        assert self.__notifier is None, 'notifier must have been reset'

        # Note: super().close() calls self._poll() repeatedly to exhaust
        # IO events.  The first call might be served by __dequeue_future;
        # the remaining calls are guaranteed to block because __notifier
        # is None.
        super().close()

        if self.__executor is not None:
            self.__executor.shutdown()
            self.__executor = None


class QiProactorEventLoop(
    _proactor_events.QiBaseProactorEventLoop,
    asyncio.windows_events.ProactorEventLoop
):
    def __init__(self, proactor=None):
        # The proactor argument is defined only for signature compatibility
        # with ProactorEventLoop.  It must be set to None.
        assert proactor is None, 'proactor must be None'
        proactor = _QiProactor()
        super().__init__(proactor)

    if sys.version_info >= (3, 8):
        # run_forever is overridden in Python 3.8 and above

        def _qi_loop_startup(self):
            # ---- BEGIN COPIED FROM ProactorEventLoop.run_forever
            assert self._self_reading_future is None
            self.call_soon(self._loop_self_reading)
            # ---- END COPIED FROM ProactorEventLoop.run_forever
            super()._qi_loop_startup()

        def _qi_loop_cleanup(self):
            super()._qi_loop_cleanup()
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


class QiProactorEventLoopPolicy(asyncio.events.BaseDefaultEventLoopPolicy):
    _loop_factory = QiProactorEventLoop


class QiSelectorEventLoop(
    _selector_events.QiBaseSelectorEventLoop,
    asyncio.windows_events.SelectorEventLoop
):
    pass


class QiSelectorEventLoopPolicy(asyncio.events.BaseDefaultEventLoopPolicy):
    _loop_factory = QiSelectorEventLoop


if sys.version_info < (3, 8):
    QiDefaultEventLoop = QiSelectorEventLoop
    QiDefaultEventLoopPolicy = QiSelectorEventLoopPolicy
else:
    QiDefaultEventLoop = QiProactorEventLoop
    QiDefaultEventLoopPolicy = QiProactorEventLoopPolicy

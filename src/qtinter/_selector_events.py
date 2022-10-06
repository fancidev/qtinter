""" _selector_events.py - Qi based on SelectorEventLoop """

import asyncio.selector_events
import concurrent.futures
import selectors
import signal
import threading
import unittest.mock
from typing import List, Optional, Tuple
from ._base_events import *
from ._selectable import _QiNotifier


__all__ = 'QiBaseSelectorEventLoop',


class _QiSelector(selectors.BaseSelector):

    def __init__(self, selector: selectors.BaseSelector):
        super().__init__()
        self._selector = selector
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._select_future: Optional[concurrent.futures.Future] = None
        self._idle = threading.Event()
        self._idle.set()
        self._notifier: Optional[_QiNotifier] = None
        self._closed = False

    def set_notifier(self, notifier: Optional[_QiNotifier]) -> None:
        self._unblock_if_blocked()
        self._notifier = notifier

    def _unblock_if_blocked(self):
        assert not self._closed, 'selector already closed'
        if not self._idle.is_set():
            assert self._notifier is not None, 'notifier expected'
            self._notifier.wakeup()
            self._idle.wait()

    def register(self, fileobj, events, data=None):
        self._unblock_if_blocked()
        return self._selector.register(fileobj, events, data)

    def unregister(self, fileobj):
        self._unblock_if_blocked()
        return self._selector.unregister(fileobj)

    def modify(self, fileobj, events, data=None):
        self._unblock_if_blocked()
        return self._selector.modify(fileobj, events, data)

    def select(self, timeout: Optional[float] = None) \
            -> List[Tuple[selectors.SelectorKey, int]]:
        assert not self._closed, 'selector already closed'

        # If the last call to select() raised _QiYield, the caller
        # (from _run_once) should only call us again after receiving a
        # notification from us, and we only send the notification after
        # entering IDLE state.
        assert self._idle.is_set(), 'unexpected select'

        # Return previous select() result (or exception) if there is one.
        if self._select_future is not None:
            try:
                return self._select_future.result()
            finally:
                self._select_future = None

        # Perform normal (blocking) select if no notifier is set.
        if self._notifier is None:
            return self._selector.select(timeout)

        # Perform normal select if timeout is zero.
        if timeout == 0:
            return self._selector.select(timeout)

        # Try select with zero timeout, and return if any IO is ready.
        event_list = self._selector.select(0)
        if event_list:
            return event_list

        # No IO is ready and caller wants to wait.  select() in a separate
        # thread and tell the caller to yield.
        self._idle.clear()
        try:
            self._select_future = self._executor.submit(self._select, timeout)
        except BaseException:
            # Should submit() raise, we assume no task is spawned.
            self._idle.set()
            raise
        else:
            return self._notifier.no_result()  # raises _QiYield

    def _select(self, timeout):
        try:
            return self._selector.select(timeout)
        finally:
            # Make a copy of self._notifier because it may be altered by
            # set_notifier immediately after self._idle is set.
            notifier = self._notifier
            self._idle.set()
            notifier.notify()

    def close(self) -> None:
        # close() is called when the loop is being closed, and the loop
        # can only be closed when it is in STOPPED state.  In this state
        # the selector must be idle.  In addition, the self pipe is
        # closed before closing the selector, so write_to_self cannot be
        # used at this point.
        if not self._closed:
            assert self._idle.is_set(), 'unexpected close'
            self._executor.shutdown()
            self._selector.close()
            self._select_future = None
            self._notifier = None
            self._closed = True

    def get_key(self, fileobj):
        self._unblock_if_blocked()
        return self._selector.get_key(fileobj)

    def get_map(self):
        self._unblock_if_blocked()
        return self._selector.get_map()


class QiBaseSelectorEventLoop(
    QiBaseEventLoop,
    asyncio.selector_events.BaseSelectorEventLoop
):
    def __init__(self, selector=None):
        if selector is None:
            selector = selectors.DefaultSelector()
        if isinstance(selector, unittest.mock.Mock):
            # Pass through mock object for testing
            qi_selector = selector
        else:
            qi_selector = _QiSelector(selector)
        super().__init__(qi_selector)

        # Similar to asyncio.BaseProactorEventLoop, install wakeup fd
        # so that select() in a separate thread can be interrupted by
        # Ctrl+C.  Only the main thread of the main interpreter may
        # install a wakeup fd, but other threads will never receive a
        # KeyboardInterrupt, so it's ok if set_wakeup_fd fails.
        self.__wakeup_fd_installed = False
        self._qi_install_wakeup_fd()

    def _qi_install_wakeup_fd(self):
        try:
            signal.set_wakeup_fd(self._csock.fileno())
        except Exception:
            self.__wakeup_fd_installed = False
        else:
            self.__wakeup_fd_installed = True

    def close(self):
        if self.is_running():
            raise RuntimeError("Cannot close a running event loop")
        # Uninstall the wakeup fd is one was installed.
        if self.__wakeup_fd_installed:
            try:
                signal.set_wakeup_fd(-1)
            except (ValueError, OSError):
                pass
            finally:
                self.__wakeup_fd_installed = False
        super().close()

""" _selector_events.py - AsyncSlot based on SelectorEventLoop """

import asyncio
import selectors
import concurrent.futures
import threading
import weakref
from typing import List, Optional, Tuple
from ._base_events import *


__all__ = 'AsyncSlotSelectorEventLoop', 'AsyncSlotSelectorEventLoopPolicy',


class AsyncSlotSelector(selectors.BaseSelector):
    def __init__(self, selector: selectors.BaseSelector,
                 write_to_self: weakref.WeakMethod):
        super().__init__()
        self._selector = selector
        self._write_to_self = write_to_self
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._select_future: Optional[concurrent.futures.Future] = None
        self._select_done = threading.Event()
        self._notifier: Optional[AsyncSlotNotifier] = None

    def set_notifier(self, notifier: Optional[AsyncSlotNotifier]) -> None:
        self._unblock_if_blocked()
        self._notifier = notifier

    def _unblock_if_blocked(self):
        if self._select_future is not None and not self._select_done.is_set():
            write_to_self = self._write_to_self()
            assert write_to_self is not None, (
                'AsyncSlotEventLoop is supposed to close AsyncSlotSelector '
                'before being deleted')
            write_to_self()
            self._select_future.result()  # waits

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

        if self._select_future is not None:
            # A prior select() call was submitted to the executor.  We only
            # submit a select() call if _run_once() calls us with a positive
            # timeout, which can only happen if there are no ready tasks to
            # execute.  That this method is called again means _run_once is
            # run again, which can only happen if we asked it to by emitting
            # the notified signal of __notifier.
            assert self._select_done.is_set(), 'unexpected select'
            try:
                return self._select_future.result()
            finally:
                self._select_done.clear()
                self._select_future = None

        # Try select with zero timeout.  If any IO is ready or if the caller
        # does not require IO to be ready, return that.
        event_list = self._selector.select(0)
        if event_list or (timeout is not None and timeout <= 0):
            return event_list

        # No IO is ready and caller wants to wait.  select() in a separate
        # thread and tell the caller to yield.
        assert self._notifier is not None, 'missing set_notifier'
        self._select_future = self._executor.submit(self._select, timeout)
        raise AsyncSlotYield

    def _select(self, timeout):
        # Any exception raised by self._selector.select() is stored in the
        # future and propagated to the next _run_once() call.
        try:
            return self._selector.select(timeout)
        finally:
            self._select_done.set()
            self._notifier.notify()

    def close(self) -> None:
        self._unblock_if_blocked()
        self._executor.shutdown()
        self._selector.close()
        # If close() is called before consuming the result of select(), the
        # result is dropped.
        self._select_future = None
        self._notifier = None

    def get_key(self, fileobj):
        self._unblock_if_blocked()
        return self._selector.get_key(fileobj)

    def get_map(self):
        self._unblock_if_blocked()
        return self._selector.get_map()


class AsyncSlotSelectorEventLoop(AsyncSlotBaseEventLoop,
                                 asyncio.SelectorEventLoop):

    def __init__(self):
        selector = AsyncSlotSelector(selectors.DefaultSelector(),
                                     weakref.WeakMethod(self._write_to_self))
        super().__init__(selector)


class AsyncSlotSelectorEventLoopPolicy(asyncio.events.BaseDefaultEventLoopPolicy):
    _loop_factory = AsyncSlotSelectorEventLoop

""" _selector_events.py - AsyncSlot based on SelectorEventLoop """

import asyncio
import concurrent.futures
import selectors
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
        self._idle = threading.Event()
        self._idle.set()
        self._notifier: Optional[AsyncSlotNotifier] = None
        self._closed = False

    def set_notifier(self, notifier: Optional[AsyncSlotNotifier]) -> None:
        self._unblock_if_blocked()
        self._notifier = notifier

    def _unblock_if_blocked(self):
        assert not self._closed, 'selector already closed'
        if not self._idle.is_set():
            write_to_self = self._write_to_self()
            assert write_to_self is not None, (
                'AsyncSlotEventLoop is supposed to close AsyncSlotSelector '
                'before being deleted')
            write_to_self()
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

        # If the last call to select() raised AsyncSlotYield, the caller
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
            raise AsyncSlotYield

    def _select(self, timeout):
        # Make a copy of self._notifier because it may be altered by
        # set_notifier immediately after self._idle is set.
        notifier = self._notifier
        try:
            return self._selector.select(timeout)
        finally:
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


class AsyncSlotSelectorEventLoop(AsyncSlotBaseEventLoop,
                                 asyncio.SelectorEventLoop):

    def __init__(self, *, standalone=True):
        selector = AsyncSlotSelector(selectors.DefaultSelector(),
                                     weakref.WeakMethod(self._write_to_self))
        super().__init__(selector, standalone=standalone)


class AsyncSlotSelectorEventLoopPolicy(asyncio.events.BaseDefaultEventLoopPolicy):
    _loop_factory = AsyncSlotSelectorEventLoop

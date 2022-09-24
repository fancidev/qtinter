""" _unix_events.py - define default loop and policy under unix """

import sys

if sys.platform == 'win32':
    raise ImportError('unix only')


import asyncio.unix_events
from . import _selector_events


__all__ = (
    'AsyncSlotDefaultEventLoop',
    'AsyncSlotDefaultEventLoopPolicy',
    'AsyncSlotSelectorEventLoop',
    'AsyncSlotSelectorEventLoopPolicy',
)


class AsyncSlotSelectorEventLoop(
    _selector_events.AsyncSlotBaseSelectorEventLoop,
    asyncio.unix_events.SelectorEventLoop
):
    def remove_signal_handler(self, sig):
        result = super().remove_signal_handler(sig)
        if not self._signal_handlers and not self._closed:
            # AsyncSlotBaseSelectorEventLoop installs a wakeup fd, but
            # _UnixSelectorEventLoop.remove_signal_handler uninstalls
            # it if there are no signal handlers.  This is not what we
            # want.  Re-install the wakeup in this case.
            self._asyncslot_install_wakeup_fd()
        return result


class AsyncSlotSelectorEventLoopPolicy(
    asyncio.unix_events.DefaultEventLoopPolicy
):
    _loop_factory = AsyncSlotSelectorEventLoop


AsyncSlotDefaultEventLoopPolicy = AsyncSlotSelectorEventLoopPolicy
AsyncSlotDefaultEventLoop = AsyncSlotSelectorEventLoop

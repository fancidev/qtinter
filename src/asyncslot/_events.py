""" _events.py - entry point for asyncslot implementation """

import asyncio
import sys

from ._selector_events import *


__all__ = ('AsyncSlotDefaultEventLoop', 'install_event_loop', )


class _EventLoopManager:
    # Taken and adapted from asyncio.runners.run()

    def __init__(self, debug=None):
        self._loop = AsyncSlotDefaultEventLoop()
        self._debug = debug

    def __enter__(self):
        self._loop.attach()
        asyncio.events.set_event_loop(self._loop)
        if self._debug is not None:
            self._loop.set_debug(self._debug)

    def __exit__(self, *args):
        loop = self._loop
        loop.detach()
        try:
            asyncio.runners._cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            asyncio.events.set_event_loop(None)
            loop.close()


def install_event_loop():
    return _EventLoopManager()


if sys.platform == 'win32':
    raise NotImplementedError
else:
    AsyncSlotDefaultEventLoop = AsyncSlotSelectorEventLoop

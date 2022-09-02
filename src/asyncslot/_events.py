""" _events.py - entry point for asyncslot implementation """

import asyncio
import sys
from typing import Callable

from ._selector_events import *


__all__ = ('AsyncSlotDefaultEventLoop', 'AsyncSlotRunner', )


# Adapted from asyncio.runners
class AsyncSlotRunner:
    """Context manager that runs an AsyncSlotDefaultEventLoop in attached
    mode."""

    def __init__(self, *, debug: Optional[bool] = None, loop_factory:
                 Optional[Callable[[], AsyncSlotBaseEventLoop]] = None):
        self._debug = debug
        self._loop_factory = loop_factory
        self._loop: Optional[AsyncSlotBaseEventLoop] = None

    def __enter__(self):
        if self._loop_factory is None:
            self._loop = AsyncSlotDefaultEventLoop()
        else:
            self._loop = self._loop_factory()
        asyncio.events.set_event_loop(self._loop)  # ???
        if self._debug is not None:
            self._loop.set_debug(self._debug)
        self._loop.__enter__()

    def __exit__(self, *args):
        self._loop.__exit__(*args)
        loop = self._loop
        try:
            asyncio.runners._cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            asyncio.events.set_event_loop(None)
            loop.close()
            self._loop = None


if sys.platform == 'win32':
    raise NotImplementedError
else:
    AsyncSlotDefaultEventLoop = AsyncSlotSelectorEventLoop

""" _runners.py - run asyncslot event loop in INTEGRATED mode """

import asyncio.runners
import sys
from typing import Callable, Optional
from ._base_events import AsyncSlotBaseEventLoop

if sys.platform == 'win32':
    from ._windows_events import AsyncSlotDefaultEventLoop
else:
    from ._unix_events import AsyncSlotDefaultEventLoop


__all__ = 'AsyncSlotRunner',


# Adapted from asyncio.runners
class AsyncSlotRunner:
    """Context manager that runs an AsyncSlotDefaultEventLoop in INTEGRATE
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
        self._loop.set_guest(True)
        asyncio.events.set_event_loop(self._loop)  # ???
        if self._debug is not None:
            self._loop.set_debug(self._debug)
        self._loop.start()

    def __exit__(self, *args):
        if self._loop.is_running():
            # Don't stop again if user code has already stopped the loop.
            self._loop.stop()
        loop = self._loop
        try:
            asyncio.runners._cancel_all_tasks(loop)
            # Note: the following steps will be run in EXCLUSIVE mode as
            # it is undesirable, and maybe even impossible, to launch a
            # Qt event loop at this point -- e.g. QCoreApplication.exit()
            # may have been called.
            loop.run_until_complete(loop.shutdown_asyncgens())
            if hasattr(loop, "shutdown_default_executor"):
                loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            asyncio.events.set_event_loop(None)
            loop.close()
            self._loop = None

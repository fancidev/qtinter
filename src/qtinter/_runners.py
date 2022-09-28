""" _runners.py - run asyncslot event loop in INTEGRATED mode """

import asyncio.runners
import sys
from typing import Callable, Optional
from ._base_events import QiBaseEventLoop

if sys.platform == 'win32':
    from ._windows_events import QiDefaultEventLoop
else:
    from ._unix_events import QiDefaultEventLoop


__all__ = 'QiRunner',


# Adapted from asyncio.runners
class QiRunner:
    """Context manager that runs an QiDefaultEventLoop in INTEGRATE
    mode."""

    def __init__(self, *, debug: Optional[bool] = None, loop_factory:
                 Optional[Callable[[], QiBaseEventLoop]] = None):
        self._debug = debug
        self._loop_factory = loop_factory
        self._loop: Optional[QiBaseEventLoop] = None

    def __enter__(self):
        if self._loop_factory is None:
            self._loop = QiDefaultEventLoop()
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

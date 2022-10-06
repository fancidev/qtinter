"""Context managers for asyncio-Qt interop"""

import asyncio.runners
import contextlib
import sys
from typing import Callable, Optional
from ._base_events import QiBaseEventLoop, QiLoopMode

if sys.platform == 'win32':
    from ._windows_events import QiDefaultEventLoop, QiDefaultEventLoopPolicy
else:
    from ._unix_events import QiDefaultEventLoop, QiDefaultEventLoopPolicy


__all__ = 'using_asyncio_from_qt', 'using_qt_from_asyncio',


@contextlib.contextmanager
def using_asyncio_from_qt(
    *,
    debug: Optional[bool] = None,
    loop_factory: Optional[Callable[[], QiBaseEventLoop]] = None
):
    # Adapted from asyncio.runners
    if loop_factory is None:
        loop = QiDefaultEventLoop()
    else:
        loop = loop_factory()

    loop.set_mode(QiLoopMode.GUEST)
    if debug is not None:
        loop.set_debug(debug)

    try:
        asyncio.events.set_event_loop(loop)
        loop.start()
        yield
    finally:
        if loop.is_running():
            # Don't stop again if user code has already stopped the loop.
            loop.stop()
        # Note: the following steps will be run in NATIVE mode because
        # it is undesirable, and maybe even impossible, to launch a
        # Qt event loop at this point -- e.g. QCoreApplication.exit()
        # may have been called.
        loop.set_mode(QiLoopMode.NATIVE)
        try:
            asyncio.runners._cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            if hasattr(loop, "shutdown_default_executor"):
                loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            asyncio.events.set_event_loop(None)
            loop.close()


@contextlib.contextmanager
def using_qt_from_asyncio():
    policy = QiDefaultEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    try:
        yield
    finally:
        asyncio.set_event_loop_policy(None)

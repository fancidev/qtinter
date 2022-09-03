""" _slot.py - definition of AsyncSlot decorator """

import asyncio
import functools
import inspect
from typing import Callable, Coroutine, Set
from ._base_events import AsyncSlotBaseEventLoop


__all__ = 'asyncSlot',


# Global variable to store strong reference to AsyncSlot tasks so that they
# don't get garbage collected during execution.
_running_tasks: Set[asyncio.Task] = set()


CoroutineFunction = Callable[..., Coroutine]


def asyncSlot(fn: CoroutineFunction):  # noqa
    """ Wrap a coroutine function to make it usable as a Qt slot. """

    if not inspect.iscoroutinefunction(fn):
        raise TypeError('asyncSlot must wrap a coroutine function')

    @functools.wraps(fn)
    def invoke(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # TODO: log warning
            raise

        if not isinstance(loop, AsyncSlotBaseEventLoop):
            raise RuntimeError(f"asyncSlot is not compatible with the "
                               f"running event loop '{loop!r}'")

        coro = fn(*args, **kwargs)
        task = loop.run_task(coro)  # TODO: set name
        _running_tasks.add(task)
        task.add_done_callback(_running_tasks.discard)

    # fn may have been decorated with Slot() or pyqtSlot().  "Carry over"
    # the decoration if so.
    # TODO: double check the field names
    if hasattr(fn, '_slots'):  # PySide6
        invoke._slots = fn._slots  # noqa
    if hasattr(fn, '__pyqtSignature__'):  # PyQt6
        invoke.__pyqtSignature__ = fn.__pyqtSignature__

    return invoke

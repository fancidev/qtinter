""" _slot.py - definition of AsyncSlot decorator """

import asyncio
import functools
import inspect
from PySide6.QtCore import Slot
from ._base_events import *
from ._selector_events import AsyncSlotSelectorEventLoop


__all__ = 'AsyncSlot',


def AsyncSlot(*slot_args, **slot_kwargs):  # noqa

    def decorator(fn):
        if not inspect.iscoroutinefunction(fn):
            raise TypeError(f'AsyncSlot can only decorate a coroutine '
                            f'function, but got {fn!r}')

        @Slot(*slot_args, **slot_kwargs)
        @functools.wraps(fn)
        def invoke_coroutine_function(*args, **kwargs):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
                # # TODO: check (or not) that there's a Qt event loop running
                # loop = AsyncSlotSelectorEventLoop()
                # # TODO: close the loop when done

            if loop is None:
                raise NotImplementedError

            if not isinstance(loop, AsyncSlotBaseEventLoop):
                raise RuntimeError(f"AsyncSlot is not compatible with the "
                                   f"running event loop '{loop!r}'")

            coro = fn(*args, **kwargs)
            loop.create_task(coro)
            # TODO: dangling task instance

        return invoke_coroutine_function

    return decorator

""" _slot.py - definition of helper functions """

import asyncio
import functools
import inspect
from typing import Callable, Coroutine, Set
from ._base_events import QiBaseEventLoop


__all__ = 'asyncslot',


# Global variable to store strong reference to tasks created by asyncslot()
# so that they don't get garbage collected during execution.
_running_tasks: Set[asyncio.Task] = set()


CoroutineFunction = Callable[..., Coroutine]


def asyncslot(fn: CoroutineFunction):  # noqa
    """ Wrap a coroutine function to make it usable as a Qt slot. """

    # TODO: support decoration on @classmethod or @staticmethod by returning
    # TODO: a wrapper method descriptor.
    if not inspect.iscoroutinefunction(fn):
        raise TypeError(f'asyncslot cannot be applied to {fn!r} because '
                        f'it is not a coroutine function')

    # Because the wrapper's signature is (*args), PySide/PyQt will always
    # call the wrapper with the signal's (full) parameter list instead of
    # the slot's parameter list if it is shorter.  We work around this by
    # "truncating" the input parameter list if needed.
    sig = inspect.signature(fn)
    params = sig.parameters

    # Parameters come in the following order of kinds (each kind is optional):
    # [POSITIONAL_ONLY]
    # [POSITION_OR_KEYWORD]
    # [VAR_POSITIONAL]
    # [KEYWORD_ONLY]
    # [VAR_KEYWORD]
    param_count = 0
    for p in params.values():
        if p.kind == p.POSITIONAL_ONLY:
            param_count += 1
        elif p.kind == p.POSITIONAL_OR_KEYWORD:
            param_count += 1
        elif p.kind == p.VAR_POSITIONAL:
            param_count = -1
        elif p.kind == p.KEYWORD_ONLY:
            if p.default is not p.empty:
                raise TypeError(f"asyncslot cannot be applied to {fn!r} "
                                f"because it contains keyword-only argument "
                                f"'{p.name} without default")
        elif p.kind == p.VAR_KEYWORD:
            pass  # **kwargs will always be empty
        else:
            assert False, f"unexpected parameter kind '{p.kind}'"

    @functools.wraps(fn)
    def asyncslot_wrapper(*args):
        loop = asyncio.events._get_running_loop()
        if loop is None:
            raise RuntimeError('cannot call asyncslot without a running loop')

        if not isinstance(loop, QiBaseEventLoop):
            raise RuntimeError(f"asyncslot is not compatible with the "
                               f"running event loop '{loop!r}'")

        # Truncate arguments if slot expects fewer than signal provides
        if 0 <= param_count < len(args):
            coro = fn(*args[:param_count])
        else:
            coro = fn(*args)

        task = loop.run_task(coro)  # TODO: set name
        _running_tasks.add(task)
        task.add_done_callback(_running_tasks.discard)

    # fn may have been decorated with Slot() or pyqtSlot().  "Carry over"
    # the decoration if so.
    if hasattr(fn, '_slots'):  # PySide2, PySide6
        asyncslot_wrapper._slots = fn._slots  # noqa
    if hasattr(fn, '__pyqtSignature__'):  # PyQt5, PyQt6
        asyncslot_wrapper.__pyqtSignature__ = fn.__pyqtSignature__

    return asyncslot_wrapper

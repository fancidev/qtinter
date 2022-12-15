""" _slot.py - definition of helper functions """

import asyncio
from typing import Callable, Coroutine, Set
from ._tasks import run_task
from ._helpers import get_positional_parameter_count, transform_slot


__all__ = 'asyncslot',


# Global variable to store strong reference to tasks created by asyncslot()
# so that they don't get garbage collected during execution.
_running_tasks: Set[asyncio.Task] = set()

CoroutineFunction = Callable[..., Coroutine]


def _run_coroutine_function(fn, args, param_count, task_runner):
    """Call coroutine function fn with no more than param_count *args and
    return a task wrapping the returned coroutine using task_factory."""

    # Truncate arguments if slot expects fewer than signal provides
    if 0 <= param_count < len(args):
        coro = fn(*args[:param_count])
    else:
        coro = fn(*args)

    task = task_runner(coro)  # TODO: set name and context
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)
    return task


def asyncslot(fn: CoroutineFunction, *, task_runner=run_task):
    """Wrap coroutine function to make it usable as a Qt slot.

    If fn is a bound method object, the returned wrapper will also be a
    bound method object.  This wrapper satisfies two properties:

    1. If a strong reference to the wrapper is held by external code,
       fn is kept alive (and so is the wrapper).

    2. If no strong reference to the wrapper is held by external code,
       the wrapper is kept alive until fn is garbage collected.  This
       will automatically disconnect any connection connected to the
       wrapper.
    """
    if not callable(fn):
        raise TypeError(f'asyncslot expects a coroutine function, '
                        f'but got non-callable object {fn!r}')

    # Because the wrapper's signature is (*args), PySide/PyQt will
    # always call the wrapper with the signal's (full) parameters
    # list instead of the slot's parameter list if it is shorter.
    # Work around this by "truncating" input parameters if needed.
    param_count = get_positional_parameter_count(fn)

    return transform_slot(fn, _run_coroutine_function, param_count, task_runner)

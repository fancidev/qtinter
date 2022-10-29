""" _slot.py - definition of helper functions """

import asyncio
import functools
import inspect
import weakref
from typing import Callable, Coroutine, Dict, Set
from ._base_events import QiBaseEventLoop


__all__ = 'asyncslot',


def _get_positional_parameter_count(fn: Callable):
    """Return the number of positional parameters of fn.  Raise TypeError
    if fn has any keyword-only parameter."""
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
            if p.default is p.empty:
                raise TypeError(f"asyncslot cannot be applied to {fn!r} "
                                f"because it contains keyword-only argument "
                                f"'{p.name}' without default")
        else:
            assert p.kind == p.VAR_KEYWORD
            pass  # **kwargs will always be empty
    return param_count


# Global variable to store strong reference to tasks created by asyncslot()
# so that they don't get garbage collected during execution.
_running_tasks: Set[asyncio.Task] = set()

CoroutineFunction = Callable[..., Coroutine]


def _run_coroutine_function(fn, param_count, args):
    """Call coroutine function fn with no more than param_count *args
    and run the returned coroutine.  Return the Task object."""
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
    return task


# Keep strong reference to async slots that have no external strong references
# but whose wrapped method object is still alive.  These objects are deleted
# when the wrapped method is deleted.
_async_slots: Dict[int, "_AsyncSlotMixin"] = dict()


class _AsyncSlotMixin:
    def __init__(self, method, param_count):
        super().__init__()
        # Make self.method available to finalizer even if weak_method fails.
        self.method = None
        # The following call raises TypeError if method.__self__ does not
        # support weak reference.  This is the same as PySide's behavior.
        # Note that PyQt raises SystemError in this case.
        self.weak_method = weakref.WeakMethod(method)
        # Keep a strong reference to method until there are no external
        # strong references to this wrapper object.
        self.method = method
        self.param_count = param_count
        self.method_name = repr(method)

    def __del__(self):
        # This finalizer is called when there are no external strong
        # references to this wrapper object.  Resurrect this object
        # by registering it in _async_slots, and then switch to a
        # weak reference to the underlying method object.
        #
        # Note: the finalizer is guaranteed to be called only once;
        # see PEP 442.  But the below code does not rely on this.
        if self.method is not None:
            _async_slots[id(self)] = self
            weakref.finalize(self.method.__self__, _async_slots.pop, id(self))
            self.method = None

    def _handle(self, *args):
        fn = self.weak_method()
        assert fn is not None, \
            f"method {self.method_name} is unexpectedly garbage collected"
        return _run_coroutine_function(fn, self.param_count, args)


def asyncslot(fn: CoroutineFunction):
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

    # Because the wrapper's signature is (*args), PySide/PyQt will always
    # call the wrapper with the signal's (full) parameter list instead of
    # the slot's parameter list if it is shorter.  We work around this by
    # "truncating" the input parameter list if needed.
    param_count = _get_positional_parameter_count(fn)

    # fn may have been decorated with Slot() or pyqtSlot():
    # - Slot() adds '_slots' to the function's __dict__.
    # - pyqtSlot() adds '__pyqtSignature__' to the function's __dict__.
    # In either case, functools.wraps() or functools.update_wrapper()
    # will update the wrapper's __dict__ with these attributes.

    if hasattr(fn, "__self__"):
        # fn is a method object.  Return a method object whose lifetime
        # is equal to that of the wrapped method, so that a connection
        # will be automatically disconnected if the wrapped object goes
        # out of scope.
        from .bindings import QtCore

        # PyQt5/6 requires decorated slot to be hosted in QObject.
        # PySide2/6 requires decorated slot to be hosted in plain object.
        if QtCore.__name__.startswith("PyQt"):
            BaseClass = QtCore.QObject
        else:
            BaseClass = object

        class _AsyncSlotWrapper(_AsyncSlotMixin, BaseClass):
            # Subclass in order to modify function's __dict__.
            def handle(self, *args):
                return super()._handle(*args)

            functools.update_wrapper(handle, fn)
            handle.__dict__.pop("__wrapped__")  # avoid strong reference

        return _AsyncSlotWrapper(fn, param_count).handle

    else:
        # fn is not a method object.  Keep a strong reference in this case.
        @functools.wraps(fn)
        def asyncslot_wrapper(*args):
            return _run_coroutine_function(fn, param_count, args)

        return asyncslot_wrapper

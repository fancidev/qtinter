"""Helper functions used by _signals.py and _slots.py"""

import functools
import inspect
import weakref
from typing import Callable, Dict


__all__ = 'get_positional_parameter_count', 'transform_slot',


# Holds strong references to SemiWeakRef objects keyed by their id().
# These SemiWeakRef objects have no external strong references to them,
# and _references keep them alive until their referent is finalized.
_references: Dict[int, "SemiWeakRef"] = dict()


class SemiWeakRef:
    """SemiWeakRef(o) is deleted when o is deleted, except that a strong
    reference to SemiWeakRef(o) in user code keeps o alive."""
    def __init__(self, o, ref=weakref.ref):
        super().__init__()  # cooperative multiple inheritance

        # Keep a strong reference to o.
        self._strong_referent = o

        # Raises TypeError if o does not support weak reference.
        self._weak_referent = ref(
            o, functools.partial(_references.pop, id(self)))

    def __del__(self):
        # The finalizer is called when there are no strong references to
        # this object.  Resurrect this object by adding it to _references.
        # Then drop the strong reference to the referent.
        #
        # Note: the finalizer is guaranteed to be called only once; see
        # PEP 442.  However, the code below does not depend on this fact.
        if self._strong_referent is not None:
            _references[id(self)] = self
            self._strong_referent = None

    def referent(self):
        return self._weak_referent()


def get_positional_parameter_count(fn: Callable) -> int:
    """Return the number of positional parameters of fn, or -1 if fn
    has a variadic positional parameter (*args).

    Raises TypeError if fn has any keyword-only parameter without a default.
    """
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


def transform_slot(slot, transform, *extra):
    """Return a callable wrapper that takes variadic arguments *args,
    such that wrapper(*arg) returns transform(slot, args, *extra).

    If slot is a bound method object, wrapper will also be a bound
    method object with the same lifetime as slot, except that a strong
    reference to wrapper keeps slot alive.

    If slot is not a bound method object, wrapper will be a function
    object that holds a strong reference to slot.
    """
    # TODO: Enclose entire function body in try...finally... to remove
    # TODO: strong reference to fn if an exception occurs.

    # fn may have been decorated with Slot() or pyqtSlot():
    # - Slot() adds '_slots' to the function's __dict__.
    # - pyqtSlot() adds '__pyqtSignature__' to the function's __dict__.
    # In either case, functools.wraps() or functools.update_wrapper()
    # will update the wrapper's __dict__ with these attributes.

    if hasattr(slot, "__self__"):
        # slot is a method object.  Return a method object whose lifetime
        # is equal to that of the receiver object of slot, so that a
        # connection will be automatically disconnected if the receiver
        # object is deleted.
        from .bindings import QtCore

        # PyQt5/6 requires decorated slots to be hosted in QObject.
        # PySide2/6 requires decorated slots to be hosted in plain object.
        if QtCore.__name__.startswith("PyQt"):
            BaseClass = QtCore.QObject
        else:
            BaseClass = object

        class _Wrapper(SemiWeakRef, BaseClass):
            # Subclass in order to modify function's __dict__.
            def handle(self, *args):
                method = self.referent()
                assert method is not None, \
                    "slot called after receiver is supposedly finalized"
                transform(method, args, *extra)

            functools.update_wrapper(handle, slot)
            handle.__dict__.pop("__wrapped__")  # remove strong ref to fn

        return _Wrapper(slot, weakref.WeakMethod).handle

    else:
        # fn is not a method object.  Keep a strong reference to it.
        @functools.wraps(slot)
        def wrapper(*args):
            return transform(slot, args, *extra)

        return wrapper

"""Helper functions for handling SIGINT"""

import functools
import signal
import sys
from typing import Any, Callable


__all__ = (
    "with_deferred_ki",
    "enable_deferred_ki",
    "disable_deferred_ki",
    "raise_deferred_ki",
)


class _Flag:
    __slots__ = '_flag',

    def __init__(self):
        self._flag = False

    def set(self) -> None:
        self._flag = True

    def is_set(self) -> bool:
        return self._flag

    def clear(self) -> None:
        self._flag = False


def with_deferred_ki(fn: Callable[..., Any]):
    """Decorates function fn so that SIGINT does not raise KeyboardInterrupt
    in the immediate body of fn.  However, if SIGINT is received in a
    function called by fn, it still raises KeyboardInterrupt.
    """
    @functools.wraps(fn)
    def wrapper(*args, deferred_ki=_Flag(), **kwargs):
        old_deferred_ki = deferred_ki
        deferred_ki = _Flag()
        if old_deferred_ki.is_set():
            deferred_ki.set()
        old_deferred_ki.clear()
        fn(*args, **kwargs)
    return wrapper


def _deferred_ki_SIGINT_handler(sig, frame):
    assert sig == signal.SIGINT
    # if frame is not None:
    #     print(frame.f_locals)
    if frame and "deferred_ki" in frame.f_locals:
        frame.f_locals["deferred_ki"].set()
    elif frame and frame.f_back and "deferred_ki" in frame.f_back.f_locals:  # pragma: no cover
        frame.f_back.f_locals["deferred_ki"].set()
    else:
        return signal.default_int_handler(sig, frame)


def enable_deferred_ki():
    # Install SIGINT handlers to enable @defer_ki decoration at runtime.
    if signal.getsignal(signal.SIGINT) is signal.default_int_handler:
        try:
            signal.signal(signal.SIGINT, _deferred_ki_SIGINT_handler)
            return True
        except (ValueError, OSError):
            pass
    return False


def disable_deferred_ki():
    # Restore SIGINT handler to system default.
    if signal.getsignal(signal.SIGINT) is _deferred_ki_SIGINT_handler:
        try:
            signal.signal(signal.SIGINT, signal.default_int_handler)
            return True
        except (ValueError, OSError):  # pragma: no cover
            pass
    return False


def raise_deferred_ki():
    assert "deferred_ki" in sys._getframe(2).f_locals, \
        "raise_deferred_ki must be called from a function " \
        "decorated with @with_deferred_ki"
    flag: _Flag = sys._getframe(2).f_locals["deferred_ki"]
    if flag.is_set():
        raise KeyboardInterrupt

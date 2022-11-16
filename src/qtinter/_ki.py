"""Helper functions for handling SIGINT"""

import functools
import signal
import sys
import threading
from typing import Any, Callable


__all__ = (
    "with_deferred_ki",
    "enable_deferred_ki",
    "disable_deferred_ki",
    "raise_deferred_ki",
)


class _Flag:
    __slots__ = '_flag',

    def __init__(self, flag=False):
        self._flag = flag

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
    def wrapper(*args, _deferred_ki_flag=_Flag(), **kwargs):
        deferred_ki_1 = _Flag()
        deferred_ki_2 = _Flag(_deferred_ki_flag.is_set())
        _deferred_ki_flag.clear()
        fn(*args, **kwargs)
    return wrapper


def _get_wrapper_frame(frame):
    if frame and not isinstance(frame.f_locals.get("_deferred_ki_flag"), _Flag):
        # frame possibly refers to decorated function
        frame = frame.f_back
    if frame and isinstance(frame.f_locals.get("_deferred_ki_flag"), _Flag):
        return frame
    else:
        return None


def _deferred_ki_SIGINT_handler(sig, frame):
    assert sig == signal.SIGINT
    # if frame is not None:
    #     print(frame.f_locals)

    frame = _get_wrapper_frame(frame)
    if frame is not None:
        deferred_ki_1 = frame.f_locals.get("deferred_ki_1")
        if isinstance(deferred_ki_1, _Flag):
            deferred_ki_1.set()
        else:
            frame.f_locals["_deferred_ki_flag"].set()
    else:
        return signal.default_int_handler(sig, frame)


def enable_deferred_ki():
    # Install SIGINT handlers to enable @defer_ki decoration at runtime.
    if threading.current_thread() is threading.main_thread():
        if signal.getsignal(signal.SIGINT) is signal.default_int_handler:
            try:
                signal.signal(signal.SIGINT, _deferred_ki_SIGINT_handler)
                return True
            except ValueError:  # pragma: no cover
                # Not all Python builds support signal.
                pass
    return False


def disable_deferred_ki():
    # Restore SIGINT handler to system default.
    if threading.current_thread() is threading.main_thread():
        if signal.getsignal(signal.SIGINT) is _deferred_ki_SIGINT_handler:
            try:
                signal.signal(signal.SIGINT, signal.default_int_handler)
                return True
            except ValueError:  # pragma: no cover
                # Not all Python builds support signal.
                pass
    return False


def raise_deferred_ki():
    frame = _get_wrapper_frame(sys._getframe(1))
    if frame is not None:
        if (frame.f_locals["deferred_ki_1"].is_set() or
                frame.f_locals["deferred_ki_2"].is_set()):
            raise KeyboardInterrupt

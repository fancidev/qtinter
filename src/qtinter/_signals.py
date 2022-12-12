"""Helper function to make Qt signal awaitable."""

import asyncio


__all__ = 'asyncsignal',


async def asyncsignal(signal):
    # signal must be a bound pyqtSignal or Signal, or an object
    # with a `connect` method that provides equivalent semantics.
    # The connection must be automatically closed when the sender
    # or the receiver object is deleted.
    #
    # We do not call disconnect() explicitly because the sender
    # might be gone when we attempt to disconnect, e.g. if waiting
    # for the 'destroyed' signal.
    from .bindings import QtCore, _QiSlotObject

    fut = asyncio.Future()

    def handler(*args):
        nonlocal slot
        if not fut.done():
            # PyQt5/6 keeps a temporary reference to the signal arguments;
            # we must make a copy of them to avoid accessing freed memory.
            # PySide2/6 keeps a copy of the arguments already.
            if hasattr(QtCore, 'QVariant'):
                # PyQt5/6 defines QVariant; PySide2/6 doesn't.
                result = tuple(QtCore.QVariant(arg).value() for arg in args)
            else:
                result = args
            fut.set_result(result)
        slot = None

    slot = _QiSlotObject(handler)
    try:
        signal.connect(slot.slot)
        return await fut
    finally:
        # In case of exception, the current frame would be stored in
        # the exception object, which would keep `slot` alive and
        # consequently keep the connection.  Set `slot` to None to
        # prevent this.
        slot = None

"""Helper function to make Qt signal awaitable."""

import asyncio


__all__ = 'asyncsignal',


async def asyncsignal(signal):
    # signal must be pyqtSignal or Signal, which automatic closes
    # the connection when the receiver object is garbage collected.
    # We do not call disconnect() explicitly because the signal
    # sender might be gone when we attempt to disconnect, such as
    # for the 'destroyed' signal.
    from .bindings import QtCore, _QiSlotObject

    fut = asyncio.Future()
    slot = _QiSlotObject()

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

            if len(result) == 0:
                fut.set_result(None)
            elif len(result) == 1:
                fut.set_result(result[0])
            else:
                fut.set_result(result)
        if slot is not None:
            slot.set_callback(None)
            slot = None

    slot.set_callback(handler)
    signal.connect(slot.invoke_callback)
    try:
        return await fut
    finally:
        if slot is not None:
            slot.set_callback(None)
            slot = None

"""Helper function to make Qt signal awaitable."""

import asyncio


__all__ = 'asyncsignal',


async def asyncsignal(signal):
    # signal must be pyqtSignal or Signal, which automatic closes
    # the connection when the receiver object is garbage collected.
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

            if len(result) == 0:
                fut.set_result(None)
            elif len(result) == 1:
                fut.set_result(result[0])
            else:
                fut.set_result(result)
        slot = None

    slot = _QiSlotObject(handler)
    signal.connect(slot.slot)
    try:
        return await fut
    finally:
        slot = None  # break cycle in case of exception

"""Helper function to make Qt signal awaitable."""

import asyncio


__all__ = 'asyncsignal',


async def asyncsignal(signal):
    # signal must be pyqtSignal or Signal
    from .bindings import QtCore

    fut = asyncio.Future()
    disconnected = False

    def handler(*args):
        nonlocal disconnected
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
        if not disconnected:
            signal.disconnect(handler)
            disconnected = True

    signal.connect(handler)
    try:
        return await fut
    finally:
        if not disconnected:
            signal.disconnect(handler)
            disconnected = True

"""Helper function to make Qt signal awaitable."""

import asyncio


__all__ = 'asyncsignal',


async def asyncsignal(signal):
    # signal must be pyqtSignal or Signal

    fut = asyncio.Future()
    disconnected = False

    def handler(*args):
        nonlocal disconnected
        if not fut.done():
            if len(args) == 0:
                fut.set_result(None)
            elif len(args) == 1:
                fut.set_result(args[0])
            else:
                fut.set_result(args)
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

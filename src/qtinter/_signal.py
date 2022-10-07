"""Helper function to make Qt signal awaitable."""

import asyncio


__all__ = 'asyncsignal',


async def asyncsignal(signal, *, copy_args=True):
    # signal must be pyqtSignal or Signal

    fut = asyncio.Future()
    disconnected = False

    def handler(*args):
        nonlocal disconnected
        if not fut.done():
            if copy_args:
                result = tuple(arg.__class__(arg) for arg in args)
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

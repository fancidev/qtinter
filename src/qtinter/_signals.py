"""Helper function to make Qt signal awaitable."""

import asyncio
import functools
from ._helpers import transform_slot


__all__ = 'asyncsignal', 'asyncsignalstream', 'multisignal',


def copy_signal_arguments(args):
    """Return a value-copy of signal arguments where necessary.

    PyQt5/6 passes a temporary reference to signal arguments to slots.
    In order to use the arguments after the slot returns, call this
    function to make a copy of them (via QVariant).  Failure to do so
    may crash the program with SIGSEGV when trying to access the
    objects later.

    PySide2/6 already passes a copy of the signal arguments to slots,
    with proper reference counting.  There is no need to copy arguments.
    """
    from .bindings import QtCore
    if hasattr(QtCore, 'QVariant'):
        # PyQt5/6 defines QVariant; PySide2/6 doesn't.
        return tuple(QtCore.QVariant(arg).value() for arg in args)
    else:
        return args


async def asyncsignal(signal):
    # signal must be a bound pyqtSignal or Signal, or an object
    # with a `connect` method that provides equivalent semantics.
    # The connection must be automatically closed when the sender
    # or the receiver object is deleted.
    #
    # We do not call disconnect() explicitly because the sender
    # might be gone when we attempt to disconnect, e.g. if waiting
    # for the 'destroyed' signal.
    from .bindings import _QiSlotObject

    fut = asyncio.Future()

    def handler(*args):
        nonlocal slot
        if not fut.done():
            fut.set_result(copy_signal_arguments(args))
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


def _asyncsignalstream_handle(queue: asyncio.Queue, *args):
    queue.put_nowait(copy_signal_arguments(args))


class asyncsignalstream:
    def __init__(self, signal):
        from .bindings import _QiSlotObject
        self._queue = asyncio.Queue()
        self._slot = _QiSlotObject(
            functools.partial(_asyncsignalstream_handle, self._queue))
        signal.connect(self._slot.slot)

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self._queue.get()


def _emit_multisignal(slot, args, value):
    slot(value, copy_signal_arguments(args))


class multisignal:
    def __init__(self, signal_map):
        self.signal_map = signal_map

    def connect(self, slot) -> None:
        for signal, value in self.signal_map.items():
            wrapper = transform_slot(slot, _emit_multisignal, value)
            signal.connect(wrapper)

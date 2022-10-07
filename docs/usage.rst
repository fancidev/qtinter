.. currentmodule:: qtinter

Usage Guide
===========

This page explains how to use :mod:`qtinter`.


.. _using-using-asyncio-from-qt:

Using :func:`using_asyncio_from_qt`
-----------------------------------


.. _using-using-qt-from-asyncio:

Using :func:`using_qt_from_asyncio`
-----------------------------------


.. _using-asyncslot:

Using :func:`asyncslot`
-----------------------

:func:`asyncslot` wraps a coroutine function (one defined by ``async def``)
to make it usable as a Qt slot. Without wrapping, a coroutine function
(whether decorated with ``QtCore.Slot``/``PyQt6.pyqtSlot`` or not)
cannot be used as a slot because calling it merely returns a coroutine
object instead of performing real work.

Under the hood, :func:`asyncslot` calls :meth:`QiBaseEventLoop.run_task`,
a custom method which creates an :class:`asyncio.Task` wrapping the
coroutine and executes it immediately until the first suspension point.

This is designed to work with a common coding pattern where some work is
performed immediately in response to a signal.  For example, the ``clicked``
handler of a "Send Order" button normally disables the button on entry
before actually sending the order over network, to avoid sending duplicate
orders.  For this to work correctly, the code until the first suspension
point must be executed immediately.

It is *not* recommended to *decorate* a coroutine function with
:func:`asyncslot`, because that would make an ``async def`` function
behave like a normal function, which is confusing.  For this reason,
:func:`asyncslot` returns ``None`` instead of :class:`asyncio.Task`,
so that you will not accidentally await a decorated async function.

If you need the :class:`asyncio.Task` instance for the running 'async slot',
call :func:`asyncio.current_task` from within the running coroutine.
The task object may be stored somewhere to cancel the coroutine later.

(From within the coroutine, raise :exc:`asyncio.CancelledError` to cancel
itself.)


.. _using-asyncsignal:

Using :func:`asyncsignal`
-------------------------



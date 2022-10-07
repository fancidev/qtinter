.. currentmodule:: qtinter

Under the Hood
==============

This page explains how :mod:`qtinter` is implemented.

We first give an overview of how ``asyncio`` works.  We then give an
overview of how Qt works.  We then explain how :mod:`qtinter` bridges
them.


.. _loop-modes:

Loop modes
----------

A :class:`qtinter.QiBaseEventLoop` has three *modes* of operations:
*owner mode*, *guest mode*, and *native mode*.

.. note::

   Both owner mode and guest mode require a ``QtCore.QCoreApplication``,
   ``QtGui.QGuiApplication`` or ``QtWidgets.QApplication`` instance to
   exist in order to run the loop.  This is because these modes use Qt's
   signals and slots to schedule callbacks.

Owner mode
~~~~~~~~~~

*Owner mode* provides 100% asyncio loop semantics and should be used
if your code calls :func:`asyncio.run` or equivalent as its entry point.
You normally launch a loop in host mode using the
:func:`qtinter.using_qt_from_asyncio` context manager.  Alternatively,
call :func:`qtinter.default_loop_factory` to create a loop in host mode
and then manipulate it manually.

.. note::

   :class:`qtinter.QiBaseEventLoop` runs a ``QtCore.QEventLoop`` when
   operating in owner mode.  If a Qt event loop is already running,
   the loop will be nested, which is not recommended.  Also, after
   ``QtCore.QCoreApplication.exit()`` is called, it is no longer
   possible to start a ``QtCore.QEventLoop``, and hence not possible
   to run a :class:`qtinter.QiBaseEventLoop` in owner mode.

Guest mode
~~~~~~~~~~

*Guest mode* is designed for Qt-driven code, and is normally activated
using the :func:`qtinter.using_asyncio_from_qt` context manager.
In guest mode, only a *logical* asyncio event loop is activated; the
*physical* Qt event loop must still be run by the application code,
e.g. by calling ``app.exec()``.

.. note::

   In guest mode, the running state of the logical asyncio event loop
   is decoupled from and independent of the running state of the physical
   Qt event loop.

Native mode
~~~~~~~~~~~

*Native mode* is activated when :external:meth:`asyncio.loop.run_forever`
is called on a :class:`qtinter.QiBaseEventLoop` object operating in guest
mode.  In native mode, a native asyncio event loop is run, and no
Qt event loop is used at all.  This is designed for running clean-up code,
possibly after ``QtCore.QCoreApplication.exec`` has been called.

.. note::

   Because no Qt event loop is running in native mode, you should not
   use any Qt objects in clean-up code.


Interleaved code
----------------

By implementing a (logical) asyncio event loop on top of a (physical)
Qt event loop, what's not changed (from the perspective of the asyncio
event loop) is that all calls (other than call_soon_threadsafe) are
still made from the same thread. This frees us from multi-threading
complexities.

What has changed, however, is that in a physical asyncio event loop,
no code can run when the scheduler (specifically, _run_once) is blocked
in select(), while in a logical asyncio event loop, a select() call that
would otherwise block yields, allowing any code to run while the loop
is "logically" blocked in select.

For example, BaseEventLoop.stop() is implemented by setting the flag
``_stopping`` to True, which is then checked at the end of the iteration
to stop the loop. This works because stop can only ever be called from
a callback, and a callback can only ever be called after select returns
and before the next iteration of _run_once. The behavior changes if select
yields and stop is called -- the event loop will not wake up until some
IO is available.

We refer to code that runs (from the Qt event loop) after select yields
and before _run_once is called again as *interleaved code*.  We must
examine and handle the implications of such code.

We do this by fitting interleaved code execution into the 'classical'
asyncio event loop model.  Specifically, we treat interleaved code as
if they were scheduled with :meth:`asyncio.loop.call_soon_threadsafe`,
which wakes up the selector and executes the code.  With some loss of
generality, we assume no IO event or timed callback is ready at the
exact same time, so that the scheduler will be put back into blocking
select immediately after the code finishes running (unless the code
calls stop).  This simplification is acceptable because the precise
timing of multiple IO or timer events should not be relied upon.

In practice, we cannot actually wake up the asyncio scheduler every
time interleaved code is executed, firstly because there's no way to
detect their execution, and secondly because doing so would be highly
inefficient.  Instead, we assume that interleaved code that does not
access the event loop object or its selector is benign enough to be
treated as independent from the asyncio event loop mechanism and may
thus be safely ignored.

This leaves us to just consider interleaved code that accesses the
event loop object or its selector and examine its impact on scheduling.
The scheduler depends on three things: the ``_ready`` queue for "soon"
callbacks, the ``_scheduled`` queue for timer callbacks, and ``_selector``
for IO events.  If the interleaved code touches any of these things,
it needs to be handled.

While the public interface of :class:`asyncio.AbstractEventLoop` has
numerous methods, the methods that modify those three things boil down
to :meth:`asyncio.loop.call_soon`, :meth:`asyncio.loop.call_at`,
:meth:`asyncio.loop.call_later`, (arguably) :meth:`asyncio.loop.stop`,
and anything that modifies the selector (proactor).  When any of these
happens, we physically or logically wake up the selector to simulate
a call to :meth:`asyncio.loop.call_soon_threadsafe`.


.. currentmodule:: qtinter

Under the Hood
==============

This page explains how :mod:`qtinter` is implemented.

We first give an overview of how :external:mod:`asyncio` works.
We then give an overview of how Qt works.  We then explain how
:mod:`qtinter` bridges the two.


.. _loop-modes:

Loop modes
----------

A :class:`QiBaseEventLoop` has three *modes of operations*:
*owner mode*, *guest mode*, and *native mode*.

.. note::

   Both owner mode and guest mode require a ``QtCore.QCoreApplication``,
   ``QtGui.QGuiApplication`` or ``QtWidgets.QApplication`` instance to
   exist in order to run the loop.  This is because these modes use Qt's
   signal-slot mechanism to schedule callbacks.

Owner mode
~~~~~~~~~~

*Owner mode* provides 100% asyncio event loop semantics.  It should be used
if your code calls :func:`asyncio.run` or equivalent as its entry point.

You normally launch a :class:`QiBaseEventLoop` in host mode using the
:func:`using_qt_from_asyncio` context manager.  Alternatively, call
:func:`new_event_loop` to create a :class:`QiBaseEventLoop` in host mode
and then manipulate it manually.

.. note::

   :class:`QiBaseEventLoop` executes a ``QtCore.QEventLoop`` when
   operating in owner mode.  If a Qt event loop is already running,
   the new loop will run nested, which may cause the usual subtle
   consequences with nested loops and therefore is not recommended.
   If you already have a Qt event loop running and want to use asyncio
   functionalities, use the :func:`using_asyncio_from_qt` context
   manager instead.

.. note::

   If ``QtCore.QCoreApplication.exit()`` has been called, it will be
   no longer possible to start a ``QtCore.QEventLoop`` and hence not
   possible to run a :class:`QiBaseEventLoop` in owner mode.  You
   may run the :class:`QiBaseEventLoop` in native mode if needed.

Guest mode
~~~~~~~~~~

*Guest mode* runs a *logical* asyncio event loop on top of a *physical*
Qt event loop.  It is designed to enable asyncio access for Qt-driven
code.

Guest mode is normally activated using the :func:`using_asyncio_from_qt`
context manager.  Under the hood, the context manager calls
:func:`new_event_loop` to create a :class:`QiBaseEventLoop` object
and then calls its :meth:`QiBaseEventLoop.set_mode` method with
argument :data:`QiLoopMode.GUEST`.

The physical Qt event loop must be run by the application code,
e.g. by calling ``app.exec()``.

.. note::

   In guest mode, the running state of the logical asyncio event loop
   is decoupled from and independent of the running state of the physical
   Qt event loop.

Native mode
~~~~~~~~~~~

A :class:`QiBaseEventLoop` in *native mode* runs a *physical* asyncio
event loop and behaves exactly like a standard asyncio event loop;
no Qt functionality is involved.

Native mode is activated by the :func:`using_asyncio_from_qt` context
manager in its clean-up code before running the coroutines to cancel
pending tasks and shutdown async generators.  This mode allows
coroutines to run even after ``QtCore.QCoreApplication.exec``
has been called.

To manually activate native mode, call :meth:`QiBaseEventLoop.set_mode`
with argument :data:`QiLoopMode.NATIVE`.

.. note::

   Because no Qt event loop is running in native mode, you should not
   use any Qt objects in this mode.  In particular, the clean-up code
   in your coroutines should work without requiring a running Qt event
   loop.


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


.. _eager-execution:

Eager execution
---------------

When the wrapper function returned by :func:`asyncslot` is called, it
calls :meth:`QiBaseEventLoop.run_task`, which creates a task wrapping
the coroutine and *eagerly executes* the first *step* of the task.

This *eager execution* feature would lead to task nesting if the wrapper
function is called from a coroutine.  Scenarios that lead to the wrapper
function being called from a coroutine include:

- directly calling or awaiting the wrapper;

- emitting a signal to which the wrapper is connected by a direct connection;

- starting a nested Qt event loop (without using :func:`modal`) on which
  a signal connected to the wrapper is emitted.

asyncio does not allow task nesting.  Yet some of the above scenarios are
valid and cannot be systematically avoided.  To make :func:`asyncslot`
useful in practice, :class:`QiBaseEventLoop` extends asyncio's semantics
to support a particular form of task nesting, namely:

   If :meth:`QiBaseEventLoop.run_task` is called when there is an active
   task running, that task is automatically 'suspended' when the call
   begins and 'resumed' after the call returns.

This extension only applies to :meth:`QiBaseEventLoop.run_task` and is
therefore "opt-in":  Code that does not call :func:`asyncslot` or
:meth:`QiBaseEventLoop.run_task` retains full compliance with asyncio's
semantics.

.. note::

   An alternative implementation of :meth:`QiBaseEventLoop.run_task`
   that is free of task nesting by construction is to execute the
   first step of the coroutine in the caller's context instead of
   in its own task context.

   The main problem with this approach is that there is no natural
   way to retrieve the task object that wraps the remainder of the
   coroutine:

   - It cannot be retrieved within the first step of the coroutine
     because a task object for the remainder is not created yet; and

   - If returned directly to the caller, it offers no advantage
     over calling :func:`asyncio.create_task` directly to obtain
     the task object.

   In addition, that part of a coroutine may run out of a task context
   (if invoked from a callback) is just surprising.

   Due to these problems, we choose the current implementation in favor
   of this alternative.


:tocdepth: 2

API Reference
=============

This page documents the public API exposed by the ``asyncslot`` module.


Usage guidelines
----------------

If your code uses Qt as its entry point and needs to integrate asyncio-based
libraries, use the :class:`asyncslot.AsyncSlotRunner` context manager.

If your code uses asyncio as its entry point and needs to use Qt objects,
call :func:`asyncio.set_event_loop_policy` and pass one of the
`event loop policy objects`_ below *before* calling the asyncio entry point,
for example :func:`asyncio.run()`.  Alternatively, starting from Python 3.11,
you may use :class:`asyncio.Runner` as the entry point and pass one of the
`event loop objects`_ below to its *loop_factory* parameter.

In addition, this module provides a few `functions`_ to make it easier to
use asyncio from Qt as well as the other way around.


Context manager
---------------


Event loop objects
------------------

.. class:: asyncslot.AsyncSlotBaseEventLoop

   Counterpart to :class:`asyncio.BaseEventLoop` implemented on top of a
   Qt event loop.

   In addition to the methods defined in :class:`asyncio.AbstractEventLoop`,
   this class defines the following additional methods:

   .. method:: run_task(coro: typing.Coroutine, *, name: typing.Optional[str] = None) -> asyncio.Task

      Similar to :func:`asyncio.create_task()` except that the first *step*
      of the coroutine is executed immediately.  Here *step* is defined as
      the first ``yield``, ``return`` or ``raise``, whichever comes first.

      .. note:: The *name* parameter is available since Python 3.8.

   .. method:: set_guest(guest: bool) -> None:

      If *guest* is ``True``, put the loop in guest mode.
      If *guest* is ``False``, put the loop in host mode.

      This method can only be called when the loop is not running and not
      closed.

      A newly created loop object is put in host mode (corresponding to
      ``guest == False``).

   .. method:: start() -> None:

      Start the loop (i.e. put it into running state) and return without
      waiting for it to stop.

      This method can only be called in guest mode and when the loop
      is not already running.


.. class:: asyncslot.AsyncSlotProactorEventLoop

   Counterpart to :class:`asyncio.ProactorEventLoop` implemented on top of
   a Qt event loop.

   *Availability*: Windows.

.. class:: asyncslot.AsyncSlotSelectorEventLoop


   Counterpart to :class:`asyncio.SelectorEventLoop` implemented on top of
   a Qt event loop.


Event loop policy objects
-------------------------

.. class:: asyncslot.AsyncSlotDefaultEventLoopPolicy

   On Python 3.7, alias to :class:`asyncslot.AsyncSlotSelectorEventLoopPolicy`.

   On Python 3.8 and above, alias to :class:`asyncslot.AsyncSlotSelectorEventLoopPolicy` on Unix, and :class:`asyncslot.AsyncSlotProactorEventLoopPolicy` on Windows.

.. class:: asyncslot.AsyncSlotProactorEventLoopPolicy

   Event loop policy that creates an :class:`asyncslot.AsyncSlotProactorEventLoop`.

   *Availability*: Windows.

.. class:: asyncslot.AsyncSlotSelectorEventLoopPolicy

   Event loop policy that creates an :class:`asyncslot.AsyncSlotSelectorEventLoop`.


Functions
---------

.. function:: asyncslot.asyncSlot(fn: typing.Callable[..., typing.Coroutine]) -> None

   Wrap a coroutine function *fn* so that it is usable as a Qt slot.

   This is a convenience function that essentially calls
   :func:`asyncslot.AsyncSlotBaseEventLoop.run_task()` to execute the
   coroutine until the first ``yield``, ``return`` or ``raise`` and
   schedule the rest for later execution.

.. function:: asyncslot.asyncSignal(signal) -> typing.Any
   :async:

   Wait until the given Qt *signal* is emitted and return the argument(s)
   passed to the signal.

   If the signal has no arguments, return ``None``.  If the signal has
   only one argument, return that argument.  If the signal has two or
   more arguments, return those arguments as a :class:`tuple`.


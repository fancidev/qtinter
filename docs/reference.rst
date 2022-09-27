API Reference
=============

This page documents the public API exposed by the ``qtinter`` module.


Guidelines
----------

If your code is Qt-driven (e.g. it calls ``app.exec()`` as its entry point)
and you want to use an asyncio-based library, enclose your Qt entry point
in the :class:`asyncslot.AsyncSlotRunner` context manager.

If your code is asyncio-driven (e.g. it calls :func:`asyncio.run()` as its
entry point) and you want to use a Qt object, call
:func:`asyncio.set_event_loop_policy` and pass one of the
`event loop policy objects`_ below *before* calling the asyncio entry point.
Alternatively, starting from Python 3.11, use :class:`asyncio.Runner` as
the entry point and pass one of the `event loop objects`_ below to its
*loop_factory* parameter.

In addition, this module provides a few `functions`_ to make it easier
to use asyncio from Qt and vice versa.


Context manager
---------------


Event loop interface
--------------------

All `event loop objects`_ below are derived from the abstract base class
:class:`qtinter.QiBaseEventLoop`.

.. _event loop methods: https://docs.python.org/3/library/asyncio-eventloop.html#event-loop-methods

.. class:: qtinter.QiBaseEventLoop

   Counterpart to (the undocumented) :class:`asyncio.BaseEventLoop` class
   implemented on top of a Qt event loop.

   In addition to the asyncio `event loop methods`_,
   this class defines the following methods for Qt interop:

   .. method:: run_task(coro: typing.Coroutine, *, name: typing.Optional[str] = None) -> asyncio.Task

      Create an :external:class:`asyncio.Task` wrapping the coroutine *coro*
      and execute it immediately until the first ``yield``, ``return`` or
      ``raise``, whichever comes earliest.  Schedule the remainer for
      later execution and return the :external:class:`asyncio.Task` object.

      *In Python 3.8 and above*: The *name* parameter is added.

   .. method:: set_guest(guest: bool) -> None:

      If *guest* is ``True``, put the loop in guest mode.
      If *guest* is ``False``, put the loop in host mode.

      This method can only be called when the loop is not running and not
      closed.

      A newly created loop object is put in host mode (corresponding to
      ``guest == False``).

   .. method:: start() -> None:

      Start the loop (i.e. put it into *running* state) and return without
      waiting for it to stop.

      This method can only be called in guest mode and when the loop
      is not already running.


Event loop objects
------------------

.. class:: qtinter.QiDefaultEventLoop

   *In Python 3.7*: alias to :class:`qtinter.QiSelectorEventLoop`.

   *In Python 3.8 and above*: alias to :class:`qtinter.QiSelectorEventLoop`
   on Unix and :class:`qtinter.QiProactorEventLoop` on Windows.

.. class:: qtinter.QiProactorEventLoop(proactor=None)

   Counterpart to :class:`asyncio.ProactorEventLoop` implemented on top of
   a Qt event loop.

   *Availability*: Windows.

.. class:: qtinter.QiSelectorEventLoop(selector=None)

   Counterpart to :class:`asyncio.SelectorEventLoop` implemented on top of
   a Qt event loop.


Event loop policy objects
-------------------------

.. class:: qtinter.QiDefaultEventLoopPolicy

   On Python 3.7, alias to :class:`qtinter.QiSelectorEventLoopPolicy`.

   On Python 3.8 and above, alias to :class:`qtinter.QiSelectorEventLoopPolicy`
   on Unix and :class:`qtinter.QiProactorEventLoopPolicy` on Windows.

.. class:: qtinter.QiProactorEventLoopPolicy

   Event loop policy that creates :class:`qtinter.QiProactorEventLoop`.

   *Availability*: Windows.

.. class:: qtinter.QiSelectorEventLoopPolicy

   Event loop policy that creates :class:`qtinter.QiSelectorEventLoop`.


Functions
---------

.. function:: qtinter.asyncslot(fn: typing.Callable[..., typing.Coroutine]) -> None

   Wrap a coroutine function *fn* so that it is usable as a Qt slot.

   When the slot is invoked, the coroutine function *fn* is called with
   the signal arguments to produce a coroutine object.  The coroutine is
   then wrapped in an :class:`asyncio.Task` and executed immediately
   until the first ``yield``, ``return`` or ``raise``, whichever comes
   earliest.  The remainder of the the coroutine is scheduled for later
   execution before the function returns.

   This function may be called without an active loop.  However, there
   must be a running :class:`qtinter.QiBaseEventLoop` when the slot is
   invoked.

.. function:: qtinter.asyncsignal(signal) -> typing.Any
   :async:

   Wait until *signal* is emitted and return the argument(s)
   passed to the signal.

   .. _PyQt5.QtCore.pyqtSignal: https://www.riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html#PyQt5.QtCore.pyqtSignal
   .. _PyQt6.QtCore.pyqtSignal: https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots.html#PyQt6.QtCore.pyqtSignal
   .. _PySide2.QtCore.Signal: https://doc.qt.io/qtforpython-5/PySide2/QtCore/Signal.html
   .. _PySide6.QtCore.Signal: https://doc.qt.io/qtforpython/PySide6/QtCore/Signal.html#PySide6.QtCore.PySide6.QtCore.Signal

   *signal* must be a Qt signal exposed by the Qt binding in use, i.e.
   one of `PyQt5.QtCore.pyqtSignal`_, `PyQt6.QtCore.pyqtSignal`_,
   `PySide2.QtCore.Signal`_ or `PySide6.QtCore.Signal`_.

   If the signal has no arguments, return ``None``.  If the signal has
   only one argument, return that argument.  If the signal has two or
   more arguments, return those arguments in a :class:`tuple`.


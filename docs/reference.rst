API Reference
=============

This page documents the public API exposed by the :mod:`qtinter` module.


Introduction
------------

:mod:`qtinter` exposes a high-level API and a low-level API.  The
high-level API is implemented based on the low-level API.  Normally
you only need the high-level API.

The high-level API provides two context managers --- you will typically
use one of them depending on your usage scenario:

* If your code is Qt-driven (e.g. by calling ``app.exec()`` as
  entry point) and you want to use an asyncio-based library, enclose
  the Qt entry point in the :func:`qtinter.using_asyncio_from_qt()`
  context manager.

* If your code is asyncio-driven (e.g. by calling :func:`asyncio.run()`
  as entry point) and you want to use a Qt object, enclose the asyncio
  entry point in the :func:`qtinter.using_qt_from_asyncio` context
  manager.

  .. note:: *In Python 3.11 and above*: If you use :class:`asyncio.Runner`
     as the entry point, pass :class:`qtinter.default_loop_factory` as
     its *loop_factory* parameter.


The high-level API also provides two helper functions to make it easier
to interp between Qt and asyncio:

* :func:`qtinter.asyncslot` wraps a coroutine function as a Qt slot.
  This is convenient in Qt-driven code.

* :func:`qtinter.asyncsignal` wraps a Qt signal as an asyncio-based
  coroutine.  This is convenient in asyncio-driven code.


High-level API
--------------

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

.. function:: qtinter.asyncslot(fn: typing.Callable[..., typing.Coroutine]) \
              -> typing.Callable[..., None]

   Wrap coroutine function *fn* so that it can be used as a Qt slot to
   be connected to a Qt signal.

   When the slot is invoked, *fn* is called with the signal arguments to
   produce a coroutine object.  The coroutine is then wrapped in an
   :class:`asyncio.Task` and executed immediately until the first ``yield``,
   ``return`` or ``raise``, whichever comes first.  The remainder of the
   coroutine is scheduled for later execution.

   This function may be called without an active loop.  However, there
   must be a running :class:`qtinter.QiBaseEventLoop` when the slot is
   invoked.

.. function:: qtinter.default_loop_factory() -> asyncio.AbstractEventLoop

   Create an asyncio-compatible event loop that runs on top of the Qt
   event loop.

.. function:: qtinter.using_asyncio_from_qt()

   Context manager that sets up the machineary for using asyncio-based
   libraries from Qt-driven code.

.. function:: qtinter.using_qt_from_asyncio()

   Context manager that sets up the machineary for using Qt components
   from asyncio-driven code.


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



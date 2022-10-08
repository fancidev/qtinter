.. currentmodule:: qtinter

API Reference
=============

:mod:`qtinter` provides the following functions and classes in its
public API:

`Context managers`_ for asyncio-Qt interop:

* :func:`using_asyncio_from_qt` enables Qt-driven code
  to use asyncio-based components.

* :func:`using_qt_from_asyncio` enables asyncio-driven code
  to use Qt-based components.


`Helper functions`_ to make interp code fit naturally into the
current coding pattern:

* :func:`asyncslot` connects a coroutine function
  to a Qt signal; useful for Qt-driven code.

* :func:`asyncsignal` makes a Qt signal *awaitable*;
  useful for asyncio-driven code.


`Loop factory`_ to create `event loop objects`_ directly:

* :func:`default_loop_factory` creates an asyncio-compatible
  event loop object that runs on top of a Qt event loop.


`Low-level classes`_ that do the actual work of bridging Qt and asyncio:

* `Event loop interface`_

* `Event loop objects`_

* `Event loop policy objects`_


Context managers
----------------

.. function:: using_asyncio_from_qt()

   Context manager that enables enclosed *Qt-driven* code to use
   asyncio-based libraries.

   Your code is *Qt-driven* if it calls ``app.exec()`` or equivalent
   as its entry point.

   Example:

   .. code-block:: python

      app = QtWidgets.QApplication([])
      with qtinter.using_asyncio_from_qt():
          app.exec()
   
.. function:: using_qt_from_asyncio()

   Context manager that enables enclosed *asyncio-driven* code to use
   Qt components.

   Your code is *asyncio-driven* if it calls :func:`asyncio.run()` or
   equivalent as its entry point.

   .. note::

      This context manager modifies the global (per-interpreter) asyncio
      event loop policy.  Do not use this context manager if your code
      uses different types of event loops from multiple threads.
      Instead, call :func:`default_loop_factory` to create an
      event loop object and run coroutines on that loop object, e.g. by
      passing it to :class:`asyncio.Runner` (available since Python 3.11).
      

Helper functions
----------------

.. function:: asyncsignal(signal, *, copy_args=True) -> typing.Any
   :async:

   Wait until *signal* is emitted and return the signal arguments.

   .. _PyQt5.QtCore.pyqtSignal: https://www.riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html#PyQt5.QtCore.pyqtSignal
   .. _PyQt6.QtCore.pyqtSignal: https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots.html#PyQt6.QtCore.pyqtSignal
   .. _PySide2.QtCore.Signal: https://doc.qt.io/qtforpython-5/PySide2/QtCore/Signal.html
   .. _PySide6.QtCore.Signal: https://doc.qt.io/qtforpython/PySide6/QtCore/Signal.html#PySide6.QtCore.PySide6.QtCore.Signal

   *signal* must be either a Qt signal exposed by the Qt binding in use,
   i.e. one of `PyQt5.QtCore.pyqtSignal`_, `PyQt6.QtCore.pyqtSignal`_,
   `PySide2.QtCore.Signal`_ or `PySide6.QtCore.Signal`_, or a 'signal-like'
   object providing ``connect()`` and ``disconnect()`` methods with Qt
   signal's semantics.  :class:`asyncsignal` always calls ``connect()``
   with a single argument.

   If the signal has no arguments, return ``None``.  If the signal has
   only one argument, return that argument.  If the signal has two or
   more arguments, return those arguments in a :class:`tuple`.

   If *copy_args* is ``True`` (the default), a copy of each signal argument
   is returned instead of the argument itself.  Copying is necessary
   if the signal argument's lifetime is valid only for the duration of
   the callback.  The copy is made by calling the argument's class
   with the argument as the sole parameter.

.. function:: asyncslot(fn: typing.Callable[..., typing.Coroutine]) \
              -> typing.Callable[..., None]

   Return a callable object wrapping coroutine function *fn* so that
   it can be connected to a Qt signal.

   When the returned callable object is invoked, *fn* is called with the
   same arguments to produce a coroutine object.  The coroutine is then
   wrapped in an :class:`asyncio.Task` and executed immediately until
   the first ``yield``, ``return`` or ``raise``, whichever comes first.
   The remainder of the coroutine is scheduled for later execution.

   A :class:`QiBaseEventLoop` must be running when the returned
   callable object is invoked.


Loop factory
------------

.. function:: default_loop_factory() -> asyncio.AbstractEventLoop

   Return a new instance of an asyncio-compatible event loop object that
   runs on top of a Qt event loop.

   Use this function instead of :func:`using_qt_from_asyncio`
   if your code uses different types of event loops from multiple threads.
   For example, starting from Python 3.11, if your code uses
   :class:`asyncio.Runner` as its entry point, pass this function as the
   *loop_factory* parameter when constructing :class:`asyncio.Runner`.


Low-level classes
-----------------

You normally do not have to use these classes directly.


Event loop interface
~~~~~~~~~~~~~~~~~~~~

All `event loop objects`_ below are derived from the abstract base class
:class:`QiBaseEventLoop`.

.. class:: QiBaseEventLoop

   Counterpart to the (undocumented) :class:`asyncio.BaseEventLoop` class,
   implemented on top of a Qt event loop.

   In addition to asyncio's :external:ref:`asyncio-event-loop-methods`,
   this class defines the following methods for Qt interop:

   .. method:: call_next(callback, *args, context=None) -> asyncio.Handle:

      Schedule *callback* to be called with *args* and *context* right
      after the current callback completes.  This method must be called
      from within a callback or coroutine.

      Unless the current callback raises :exc:`KeyboardInterrupt` or
      :exc:`SystemExit`, *callback* is guaranteed to be called in the
      same loop iteration (without additional polling or interleaved
      code).

      If this method is called multiple times, the callbacks will be
      invoked in reverse order (i.e. last-in-first-out).

   .. method:: run_task(coro: typing.Coroutine, *, name: typing.Optional[str] = None) -> asyncio.Task

      Create an :external:class:`asyncio.Task` wrapping the coroutine
      *coro* and execute it immediately until the first ``yield``,
      ``return`` or ``raise``, whichever comes first.  The remainder
      of the coroutine is scheduled for later execution.  Return the
      :external:class:`asyncio.Task` object.

      *In Python 3.8 and above*: Added the *name* parameter.

   .. method:: set_mode(mode: QiLoopMode) -> None:

      Set loop operating mode to *mode*.

      This method can only be called when the loop is not closed and
      not running, and no stop is pending.

      A newly created loop object is in :data:`QiLoopMode.OWNER` mode.

   .. method:: start() -> None:

      Start the loop (i.e. put it into *running* state) and return without
      waiting for it to stop.

      This method can only be called in guest mode and when the loop
      is not already running.

.. class:: QiLoopMode

   An :external:class:`enum.Enum` that defines the possible operating
   modes of a :class:`QiBaseEventLoop`.  Its members are:

   .. data:: OWNER

      Appropriate for use with asyncio-driven code.

   .. data:: GUEST

      Appropriate for use with Qt-driven code.

   .. data:: NATIVE

      Appropriate for running clean-up code.

   For details on the semantics of these modes, see :ref:`loop-modes`.


Event loop objects
~~~~~~~~~~~~~~~~~~

.. class:: QiDefaultEventLoop

   *In Python 3.7*: alias to :class:`QiSelectorEventLoop`.

   *In Python 3.8 and above*: alias to :class:`QiSelectorEventLoop`
   on Unix and :class:`QiProactorEventLoop` on Windows.

.. class:: QiProactorEventLoop(proactor=None)

   Counterpart to :class:`asyncio.ProactorEventLoop`, implemented on top of
   a Qt event loop.

   *Availability*: Windows.

.. class:: QiSelectorEventLoop(selector=None)

   Counterpart to :class:`asyncio.SelectorEventLoop`, implemented on top of
   a Qt event loop.


Event loop policy objects
~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: QiDefaultEventLoopPolicy

   On Python 3.7, alias to :class:`QiSelectorEventLoopPolicy`.

   On Python 3.8 and above, alias to :class:`QiSelectorEventLoopPolicy`
   on Unix and :class:`QiProactorEventLoopPolicy` on Windows.

.. class:: QiProactorEventLoopPolicy

   Event loop policy that creates :class:`QiProactorEventLoop`.

   *Availability*: Windows.

.. class:: QiSelectorEventLoopPolicy

   Event loop policy that creates :class:`QiSelectorEventLoop`.



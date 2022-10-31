.. currentmodule:: qtinter

Developer Guide
===============

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

:func:`asyncslot` is a helper function that wraps a :term:`coroutine
function` into a normal function, which may then be connected to
a Qt signal.

It is useless to connect a coroutine function (decorated with
``Slot``/``pyqtSlot`` or not) *directly* to a Qt signal because calling
it merely returns a coroutine object rather than performing real work.

By wrapping a coroutine function with :func:`asyncslot` and connecting
the resulting wrapper to a Qt signal, the coroutine function will be
called with the signal arguments when the signal is emitted.  The
returned coroutine object is then wrapped in an :class:`asyncio.Task`
and executed immediately until the first ``yield``, ``return`` or ``raise``,
whichever comes first.  The remainder of the coroutine is scheduled for
later execution.

The recommended pattern for using :func:`asyncslot` is as follows:

1. Write the coroutine function that implements the business logic.
   In this function, store the running :class:`asyncio.Task` instance
   for cancellation later.

2. Connect the coroutine function to a Qt signal by wrapping it with
   :func:`asyncslot`.

3. Cancel the running task when a 'cancel signal' is emitted.

4. Cancel the running task when it is no longer needed (e.g. when the
   window is closed).

We demonstrate this pattern using a simple *Stopwatch* example, which
looks like the following:

.. image:: _static/stopwatch.gif

This sample application has a START button, a STOP button and an
LCD display to display the time elapsed.  The 'core' of the app
is a coroutine (``_tick``) that updates the LCD display constantly:

.. code-block:: python

   async def _tick(self):
       t0 = time.time()
       while True:
           t = time.time()
           self.lcdNumber.display(format(t - t0, ".1f"))
           await asyncio.sleep(0.05)

The steps of the pattern are implemented as follows:

1. Implement the logic of the stopwatch in a coroutine function
   (``_start``).  Store the running :class:`asyncio.Task` instance
   on entry.

   .. code-block:: python

      async def _start(self):
          self.task = asyncio.current_task()
          self.startButton.setEnabled(False)
          self.stopButton.setEnabled(True)
          try:
              await self._tick()
          finally:
              self.startButton.setEnabled(True)
              self.stopButton.setEnabled(False)

2. Connect the START button to this coroutine function (``_start``)
   by wrapping it with :class:`asyncslot`.

   .. code-block:: python

      def __init__(self):
          ...
          self.startButton.clicked.connect(qtinter.asyncslot(self._start))
          ...

3. Cannect the STOP button to a plain slot (``_stop``) to cancel
   the running task.

   .. code-block:: python

      def _stop(self):
          self.task.cancel()

4. Cancel the running task (if any) when the widget is closed.

   .. code-block:: python

      def closeEvent(self, event):
          if self.task is not None and not self.task.done():
              self.task.cancel()
          event.accept()

**Always cancel a task when it is no longer needed.**
:func:`asyncslot` keeps a strong reference to all running tasks
it starts.  If you don't cancel a task explicitly, the task will
keep running until the :func:`using_asyncio_from_qt` exits.

*Remark*. It is possible to *decorate* a coroutine function with
:class:`asyncslot` and connect the decorated function directly
to a Qt signal.  However, this approach is not recommended because
**a decorated coroutine function is transformed into a regular function**
--- this leads to subtle semantic differences and is confusing.

.. note::

   :func:`asyncslot` relies on two extensions of asyncio's semantics
   to work:

   1. *Eager task execution*.
      The first *step* of a task created by :func:`asyncslot` is executed
      immediately rather than scheduled for later execution.  This extension
      is made to support a common pattern where some work is done immediately
      in response to a signal, such as updating UI states in the above example.

   2. *Nested task execution*.
      If a coroutine function wrapped by :func:`asyncslot` is called
      from a coroutine (e.g. as the result of a signal being emitted),
      the coroutine's task is 'suspended' when the call begins and
      'resumed' after the call returns.
      This extension is made to make :func:`asyncslot` more flexible
      in practice.

   See :ref:`eager-execution` for details about these semantic extensions.


.. _using-asyncslot-without:

If you prefer to stick to asyncio's API and semantics, it is also perfectly
possible to schedule coroutines without using :func:`asyncslot`.  Reusing
the *Stopwatch* example above, this involves the following key steps:

1. Connect the START button to a plain slot (``_start``). 
   In this slot, update the UI states, schedule the coroutine using
   :func:`asyncio.create_task`, and hook the task's "done callback"
   to a clean-up routine (``_stopped``).

   .. code-block:: python

      def __init__(self):
          ...
          self.startButton.clicked.connect(self._start)
          ...

      def _start(self):
          self.startButton.setEnabled(False)
          self.stopButton.setEnabled(True)
          self.task = asyncio.create_task(self._tick())
          self.task.add_done_callback(self._stopped)

   .. note::

      Code that disables the START button cannot be moved into
      ``_tick()``, because it must be executed immediately when the
      button is clicked.

      Consequently, code that restores the UI states cannot be moved
      into ``_tick()``, because the task might be cancelled before it
      starts running.  The solution is to install a "done callback".

2. Restore UI states in the done callback (``_stopped``).

   .. code-block:: python

      def _stopped(self, task: asyncio.Task):
          self.startButton.setEnabled(True)
          self.stopButton.setEnabled(False)

#. (Same as before) Connect the STOP button to a plain slot (``_stop``)
   to cancel the running task.

   .. code-block:: python

      def _stop(self):
          self.task.cancel()

4. (Same as before) Cancel the running task (if any) when the widget
   is closed.

   .. code-block:: python

      def closeEvent(self, event):
          if self.task is not None and not self.task.done():
              self.task.cancel()
          event.accept()

Again, **always cancel a task when it is no longer needed.**
Otherwise the task may keep running in the background until
:func:`using_asyncio_from_qt` exits (or gets garbage-collected
at an arbitrary point).


.. _using-asyncsignal:

Using :func:`asyncsignal`
-------------------------


.. _using-modal:

Using :func:`modal`
-------------------


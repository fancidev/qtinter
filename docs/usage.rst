Usage
=====

This page contains a detailed description of using :mod:`qtinter`.


Installation
------------

:mod:`qtinter` is installed via ``pip``:

.. code-block:: console

   $ pip install --update qtinter

.. note::

   The ``--update`` option upgrades an existing ``qtinter`` installation
   (if any) to the latest version.

The above command does *not* install any Qt bindings because it is
assumed that you are already using some binding in your codebase.
If this is not the case, you may install a Qt binding together with
:mod:`qtinter` with the followinng command:

.. code-block:: console

   $ pip install qtinter[PyQt6]

Replace ``PyQt6`` with one of ``PyQt5``, ``PyQt6``, ``PySide2`` or
``PySide6`` of your choice.


Standard Usage
--------------

``asyncslot`` implements a *logical* asyncio event loop inside a *physical*
Qt event loop, so that asyncio-based Python libraries can be used by
a Python/Qt application.

``asyncslot`` allows you to connect a coroutine function to a signal,
like a normal slot.  A coroutine function normally cannot be connected
to a signal because calling it merely returns a coroutine object instead
of doing real work.


Operating modes
---------------

A :class:`qtinter.QiBaseEventLoop` has three modes of operations:
*host mode*, *guest mode*, and *legacy mode*.

.. note::

   Both host and guest mode require a (global) ``QtCore.QCoreApplication``,
   ``QtGui.QGuiApplication`` or ``QtWidgets.QApplication`` instance to exist
   before *running* the loop.  This is because these modes rely on Qt signals
   and slots, which require a global application instance to function.

Host mode
~~~~~~~~~

*Host mode* provides 100% asyncio loop semantics and should be used
if your code calls :func:`asyncio.run` or equivalent as its entry point.
You normally launch a loop in host mode using the
:func:`qtinter.using_qt_from_asyncio` context manager.  Alternatively,
call :func:`qtinter.default_loop_factory` to create a loop in host mode
and then manipulate it manually.

.. note::

   :class:`qtinter.QiBaseEventLoop` runs a ``QtCore.QEventLoop`` when
   operating in host mode.  If a Qt event loop is already running,
   the loop will be nested, which is not recommended.  Also, after
   ``QtCore.QCoreApplication.exit()`` is called, it is no longer
   possible to start a ``QtCore.QEventLoop``, and hence not possible
   to run a :class:`qtinter.QiBaseEventLoop` in host mode.

Guest mode
~~~~~~~~~~

*Guest mode* is designed for Qt-driven code, and is normally activated
using the :func:`qtinter.using_asyncio_from_qt` context manager.
In guest mode, only a *logical* asyncio event loop is activated; the
*physical* Qt event loop must still be run by the application code,
e.g. by calling ``app.exec()``.

.. note::

   Keep in mind that the running state of the logical asyncio event loop
   is decoupled from and independent of the running state of the physical
   Qt event loop when operating in guest mode.

Legacy mode
~~~~~~~~~~~

*Legacy mode* is activated when :external:meth:`asyncio.loop.run_forever`
is called on a :class:`qtinter.QiBaseEventLoop` object operating in guest
mode.  In legacy mode, an 'authentic' asyncio event loop is run, and no
Qt event loop is used at all.  This is designed for running clean-up code,
possibly after ``QtCore.QCoreApplication.exec`` has been called.

.. note::

   Because no Qt event loop is running in legacy mode, you should not
   use any signal-slot mechanism in clean-up code.



Qt binding lookup
-----------------

:mod:`qtinter` checks for the Qt binding used by the process
(interpreter) the first time a :func:`qtinter.QiBaseEventLoop`
is run.  It remembers this binding afterwards.

If exactly one of PyQt5, PyQt6, PySide2 or PySide6 is imported in
``sys.modules`` at the time of binding lookup, it is chosen.  This is
the default scenario that works with most workflow.

If none of the above modules are imported at the time of lookup,
the environment variable ``QTINTERBINDING`` is checked.  If it is
set to one of PyQt5, PyQt6, PySide2 or PySide6, that binding is used;
otherwise, :external:exc:`ImportError` is raised.

If more than one supported binding modules are imported at the time of
lookup, :external:exc:`ImportError` is raised.

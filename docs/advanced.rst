.. currentmodule:: qtinter

Advanced Topics
===============

:mod:`qtinter` implements a *logical* asyncio event loop on top of a
*physical* Qt event loop, allowing Qt objects and asyncio coroutines
to run in the same thread and thus integrate seamlessly.

Best Practice
-------------

Clean-up
--------

The :func:`using_asyncio_from_qt` context manager handles clean-up
automatically.  The :func:`using_qt_from_asyncio` context manager
restores the default event loop policy upon exit; loop-level clean-up
is handled by :func:`asyncio.run`.

If you create and manipulate a :class:`QiBaseEventLoop` directly,
you should do the proper clean-up after it is no longer used.  The
steps are:

1. Cancel all pending tasks.

2. Wait for all pending tasks to complete.

3. Run :meth:`asyncio.loop.shutdown_asyncgens`.

4. Run :meth:`asyncio.loop.shutdown_default_executor` (since Python 3.9).

5. Call :meth:`asyncio.loop.close`.

Steps 2-4 are coroutines and therefore must be run from within the event
loop.

.. note::

   At the point of clean-up, a Qt event loop may no longer exist and
   is not creatable if ``QCoreApplication.exit()`` has been called.
   Therefore the :func:`using_asyncio_from_qt` context manager runs
   Steps 2-4 in a *physical* asyncio event loop.


Qt binding resolution
---------------------

:mod:`qtinter` checks for the Qt binding used by the process
(interpreter) the first time a :func:`qtinter.QiBaseEventLoop`
is run.  It remembers this binding afterwards.

If exactly one of ``PyQt5``, ``PyQt6``, ``PySide2`` or ``PySide6`` is
imported in :external:data:`sys.modules` at the time of binding lookup,
it is chosen.

If none of the above modules are imported at the time of lookup,
the environment variable ``QTINTERBINDING`` is checked.  If it is
set to one of ``PyQt5``, ``PyQt6``, ``PySide2`` or ``PySide6``,
that binding is used; otherwise, :external:exc:`ImportError` is raised.

If more than one supported binding modules are imported at the time of
lookup, :external:exc:`ImportError` is raised.


Handling keyboard interrupt
---------------------------


Writing portable code
---------------------


Related libraries
-----------------

qasync, qtrio, qtpy, bindings, uvloop

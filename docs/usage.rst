Usage
=====

This page explains how to use ``asyncslot`` in detail.


Installation
------------

``asyncslot`` is a simple Python package and can be installed via ``pip``:

.. code-block:: console

   (.venv) $ pip install asyncslot

The above does *not* install any Qt bindings because it is assumed that
you already have a Python/Qt codebase using your Qt binding of choice
and ``asyncslot`` will simply work with that.

.. note::

   ``asyncslot`` supports all of the popular Qt bindings, namely
   PyQt5, PyQt6, PySide2 and PySide6.

If you have not installed any Qt binding, install one e.g. by

.. code-block:: console

   (.venv) $ pip install PyQt6

If you don't know which Qt binding to install, pick PyQt6 if you're ok
with GPL License, or pick PySide6 to go with LGPL License.  (Both offer
a commercial license alternative, by the way.)  You may also check the
:doc:`bindings` page to learn about the subtle (but immaterial)
differences between those bindings.

Finally, it's worth mentioning that you can install a Qt binding at
the same time of installing ``asyncslot``, by

.. code-block:: console

   (.venv) $ pip install asyncslot[PyQt6]

.. note::

   It is good practice to install ``asyncslot`` (or *any* Python package)
   in a virtual environment.  The above command line prompts start with
   ``(.venv)`` to indicate that a virtual environment is activated.


Standard Usage
--------------

``asyncslot`` implements a *logical* asyncio event loop inside a *physical*
Qt event loop, so that asyncio-based Python libraries can be used by
a Python/Qt application.

``asyncslot`` is designed to be as intuitive to the user (developer)
as possible.  You're expected to know how to write a Python/Qt program
and how to write a coroutine that uses asyncio-based libraries; but
we don't want you to spend more than five minutes to learn how to put
them together to work, and we don't want you to have to refactor your
existing Python/Qt code or asyncio code to make it work.  It should
just work effortlessly.

``asyncslot`` allows you to connect a coroutine function to a signal,
like a normal slot.  A coroutine function normally cannot be connected
to a signal because calling it merely returns a coroutine object instead
of doing real work.


Qt Binding Lookup
-----------------

``asyncslot`` checks for the Qt binding used by the application the
first time an ``AsyncSlotEventLoop`` is run.  It remembers this binding
afterwards.

If exactly one of PyQt5, PyQt6, PySide2 or PySide6 is imported in
``sys.modules`` at the time of binding lookup, it is chosen.  This is
the default scenario that works with most workflow.

If none of the above modules are imported at the time of lookup,
the environment variable ``ASYNCSLOT_QTBINDING`` is checked.  If it is
set to one of PyQt5, PyQt6, PySide2 or PySide6, that binding is used.
Otherwise, an ``ImportError`` is raised.

If more than one supported binding modules are imported at the time of
lookup, an ``ImportError`` is raised.

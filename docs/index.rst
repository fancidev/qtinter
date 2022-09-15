asyncslot - integrating asyncio into Python/Qt effortlessly
===========================================================

``asyncslot`` is a Python module that allows you to use asyncio-based
libraries in Python/Qt applications, effortlessly.


Quickstart
----------

Starting with an existing Python/Qt application, integrating asyncio
coroutines is as simple as installing this package and adding three
lines of code:

Step 0. Install package:

.. code-block:: console

   (.venv) $ pip install asyncslot

Step 1. Import ``asyncslot``:

.. code-block:: python

   import asyncslot

Step 2. Enclose your existing ``app.exec()`` inside a context manager:

.. code-block:: python

   with asyncslot.AsyncSlotRunner():
       sys.exit(app.exec())

Step 3: Connect any coroutine function to a signal by wrapping it in
``asyncSlot``:

.. code-block:: python

   my_signal.connect(asyncslot.asyncSlot(my_coroutine_function))

And that's it!

If you're interested to know how ``asyncslot`` is implemented, check
out the following pages for details:

.. toctree::
   :maxdepth: 2

   usage
   examples
   internals
   bindings
   reference


Requirements
------------

``asyncslot`` supports the following:

- Python version: 3.7 or higher

- Qt binding: PyQt5, PyQt6, PySide2, PySide6

- Operating system: Linux, MacOS, Windows


License
-------

BSD License.


History
-------

``asyncslot`` is derived from qasync_ but rewritten from scratch. qasync
is a fork of asyncqt_, which is a fork of quamash_.

.. _qasync: https://github.com/CabbageDevelopment/qasync
.. _asyncqt: https://github.com/gmarull/asyncqt
.. _quamash: https://github.com/harvimt/quamash


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

asyncslot --- Seamless integration of asyncio and Qt for Python
===============================================================

``asyncslot`` is a Python module that allows you to use asyncio-based
libraries in Qt for Python code, and vice versa.

``asyncslot`` strives to be **simple** and **reliable** to use:

* *Simple*: You only need to add **a few lines of code** to use asyncio
  from Qt or the other way around.  **No refactoring** of your existing
  codebase is necessary.

* *Reliable*: The module passes the **entire asyncio test suite**.
  Reassured your favorite asyncio-based library **will work**.


Installation
------------

``asyncslot`` is installed via ``pip`` from the command line:

.. code-block:: console

   $ pip install asyncslot


Using asyncio from Qt
---------------------

If you have a Qt for Python codebase and want to use an asyncio-based
library, follow these steps:


Step 1 - import ``asyncslot``.

.. code-block:: python

   import asyncslot


Step 2 - enclose your existing ``app.exec()`` inside an ``AsyncSlotRunner()``
context manager.

.. code-block:: python

   with asyncslot.AsyncSlotRunner():
       app.exec()


Step 3 (optional) - connect coroutine functions to signals by wrapping
them with ``asyncSlot``.

.. code-block:: python

   my_signal.connect(asyncslot.asyncSlot(my_coroutine_function))


And that's it!

Let's put the above together into a minimal working example
(``examples/minimal_gui.py``):

.. code-block:: python

   import asyncio
   import asyncslot  # <-- step 1 - import module
   from PyQt6 import QtWidgets

   async def say_hi():
       await asyncio.sleep(1)
       QtWidgets.QMessageBox.information(None, "Demo", "Hi")

   app = QtWidgets.QApplication([])

   button = QtWidgets.QPushButton()
   button.setText('Say Hi in one second')
   button.clicked.connect(asyncslot.asyncSlot(say_hi))  # <-- step 3 - wrap slot
   button.show()

   with asyncslot.AsyncSlotRunner():  # <-- step 2 - enclose in context manager
       app.exec()


Using Qt from asyncio
---------------------

If you have an asyncio-based Python codebase and want to use a Qt
component, follow these steps.


Step 1 - import ``asyncslot``.

.. code-block:: python

   import asyncslot


Step 2 - create a global ``QtCore.QCoreApplication``
(or ``QtWidgets.QApplication``) instance.

.. code-block:: python

   from PyQt6 import QtCore
   app = QtCore.QCoreApplication([])


Step 3 - activate ``AsyncSlotDefaultEventLoopPolicy``.

.. code-block:: python

   import asyncio
   asyncio.set_event_loop_policy(asyncslot.AsyncSlotDefaultEventLoopPolicy())


And that's it!  You can now use Qt components in your asyncio-based code.



Requirements
------------

``asyncslot`` supports the following:

- Python version: 3.7 and higher

- Qt binding: PyQt5, PyQt6, PySide2, PySide6

- Operating system: Linux, MacOS, Windows


License
-------

BSD License.


History
-------

``asyncslot`` is derived from qasync_ but rewritten from scratch. qasync_
is derived from asyncqt_, which is derived from quamash_.

.. _qasync: https://github.com/CabbageDevelopment/qasync
.. _asyncqt: https://github.com/gmarull/asyncqt
.. _quamash: https://github.com/harvimt/quamash


Further reading
---------------

Check out the following pages for details on using ``asyncslot``
as well as its internals:

.. toctree::
   :maxdepth: 2

   usage
   examples
   internals
   bindings
   reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

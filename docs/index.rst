.. module:: qtinter
   :synopsis: Interop between asyncio and Qt for Python

qtinter --- Interop between asyncio and Qt for Python
=====================================================

:mod:`qtinter` is a Python module that brings together asyncio and Qt
for Python, allowing you to use one from the other seamlessly.

:mod:`qtinter` strives to be **simple** and **reliable**:

* *Simple*: You only need to add **a few lines** of code to use asyncio
  from Qt and vice versa.  **No refactoring** of your existing codebase
  is required.

* *Reliable*: :mod:`qtinter` runs on top of a Qt event loop and passes
  the **entire asyncio test suite**.  Rest assured that your favorite
  asyncio or Qt component **will work**.


Installation
------------

.. code-block:: console

   $ pip install qtinter


Using asyncio from Qt
---------------------

If your code uses Qt as its entry point (e.g. by calling ``app.exec()``)
and you want to use an asyncio-based library, follow these steps.


Step 1 --- import :mod:`qtinter`:

.. code-block:: python

   import qtinter


Step 2 --- enclose the Qt entry point inside
:func:`qtinter.using_asyncio_from_qt` context manager:

.. code-block:: python

   app = QtWidgets.QApplication([])
   with qtinter.using_asyncio_from_qt():
       app.exec()


Step 3 --- (optionally) connect coroutine functions to Qt signals by
wrapping them with :func:`qtinter.asyncslot`:

.. code-block:: python

   my_signal.connect(qtinter.asyncslot(my_coroutine_function))


And that's it!


To see these in action, check out the :ref:`hello-world-example` and the
:ref:`http-client-example`.


Using Qt from asyncio
---------------------

If your code uses asyncio as its entry point (e.g. by calling
:func:`asyncio.run()`) and you want to use a Qt component, follow these steps.


Step 1 --- import :mod:`qtinter`:

.. code-block:: python

   import qtinter


Step 2 --- enclose the asyncio entry point inside
:func:`qtinter.using_qt_from_asyncio` context manager:

.. code-block:: python

   app = QtWidgets.QApplication([])
   with qtinter.using_qt_from_asyncio():
       asyncio.run(my_coro())


Step 3 --- (optionally) wait for Qt signals by wrapping them with
:func:`qtinter.asyncsignal`:

.. code-block:: python

   await qtinter.asyncsignal(button.clicked)


And that's it!


To see these in action, check out the :ref:`read-out-example` and the
:ref:`where-am-i-example`.


Requirements
------------

:mod:`qtinter` supports the following:

- Python version: 3.7 and higher

- Qt binding: PyQt5, PyQt6, PySide2, PySide6

- Operating system: Linux, MacOS, Windows


License
-------

BSD License.


History
-------

:mod:`qtinter` is derived from qasync_ but rewritten from scratch. qasync_
is derived from asyncqt_, which is derived from quamash_.

.. _qasync: https://github.com/CabbageDevelopment/qasync
.. _asyncqt: https://github.com/gmarull/asyncqt
.. _quamash: https://github.com/harvimt/quamash


Contents
--------

.. toctree::
   :maxdepth: 2

   usage
   examples
   internals
   bindings
   reference


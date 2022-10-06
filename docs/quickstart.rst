.. currentmodule:: qtinter

Getting Started
===============

This section shows the essentials of :mod:`qtinter` and gets you up
and running in five minutes.


Requirements
------------

:mod:`qtinter` supports the following:

- Python version: 3.7 and higher

- Qt binding: PyQt5, PyQt6, PySide2, PySide6

- Operating system: Linux, MacOS, Windows



Installation
------------

:mod:`qtinter` is installed via ``pip``:

.. code-block:: console

   $ pip install qtinter

The above command does *not* install any Qt bindings because it is
assumed that you already have one.  If that's not the case, you may
install a Qt binding together with :mod:`qtinter` using the
following command:

.. code-block:: console

   $ pip install qtinter[PyQt6]

Replace ``PyQt6`` with one of ``PyQt5``, ``PyQt6``, ``PySide2`` or
``PySide6`` of your choice.


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
For usage details, see :ref:`using-using-asyncio-from-qt` and
:ref:`using-asyncslot`.


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
For usage details, see :ref:`using-using-qt-from-asyncio` and
:ref:`using-asyncsignal`.


License
-------

BSD License.


Contributing
------------

.. _GitHub: https://github.com/fancidev/qtinter

The source code is hosted on `GitHub`_.  Please raise an issue if you have
any questions.  Pull requests are more than welcome!


Credits
-------

:mod:`qtinter` is derived from qasync_ but rewritten from scratch. qasync_
is derived from asyncqt_, which is derived from quamash_.

.. _qasync: https://github.com/CabbageDevelopment/qasync
.. _asyncqt: https://github.com/gmarull/asyncqt
.. _quamash: https://github.com/harvimt/quamash


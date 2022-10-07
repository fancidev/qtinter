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

Read on for detailed documentation on :mod:`qtinter`.

.. toctree::
   :maxdepth: 2

   quickstart
   examples
   usage
   advanced
   reference
   internals

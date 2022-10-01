Examples
========

This page shows a few examples that demonstrate the usage of :mod:`qtinter`.

.. toctree::


.. _hello-world-example:

Hello World Example
-------------------

This is a minimal example that uses :func:`asyncio.sleep` to draw an
animation in a Qt app.

.. image:: hello_world.gif

Source code (with :mod:`qtinter` API highlighted):

.. toggle::

   .. literalinclude:: ../examples/hello_world.py
      :language: python
      :emphasize-lines: 4,15,33
      :linenos:


.. _http-client-example:

Http Client Example
-------------------

This example shows how to download a web page asynchronously using the
``httpx`` module and optionally cancel the download.

.. image:: http_client.gif

Source code (with :mod:`qtinter` API highlighted):

.. toggle::

   .. literalinclude:: ../examples/http_client.py
      :language: python
      :emphasize-lines: 4,68,210
      :linenos:


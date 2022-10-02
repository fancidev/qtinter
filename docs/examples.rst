Examples
========

This page shows a few examples that demonstrate the usage of :mod:`qtinter`.

The source code is listed for each example.  Lines that demonstrate the usage
of :mod:`qtinter`'s API are highlighted.

.. toctree::


.. _hello-world-example:

Hello World Example
-------------------

This is a minimal example that uses :func:`asyncio.sleep` to draw an
animation in a Qt app.

.. image:: hello_world.gif

Source code:

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

Source code:

.. toggle::

   .. literalinclude:: ../examples/http_client.py
      :language: python
      :emphasize-lines: 4,68,210
      :linenos:


.. _read-out-example:

Read Out Example
----------------

This example shows how to use a Qt component (``QtTextToSpeech`` in this
case) in asyncio-driven code.

Sample output (on macOS 12):

.. code-block:: console

   $ python examples/read_out.py -h
   usage: examples/read_out.py [options]
   Read out text from stdin.
   Options:
       -e          Echo each line before reading it out
       -h          Show this screen and exit
       -l locale   One of en_US, fr_FR (default: en_US)
       -p pitch    Number between -1.0 and +1.0 (default: 0.0)
       -r rate     Number between -1.0 and +1.0 (default: 0.0)
       -v voice    One of Alex, Fiona, Fred, Samantha, Victoria (default: Alex)

Source code:

.. toggle::

   .. literalinclude:: ../examples/read_out.py
      :language: python
      :emphasize-lines: 5,21,72
      :linenos:


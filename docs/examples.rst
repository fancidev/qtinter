.. currentmodule:: qtinter

Examples
========

This page shows a few examples that demonstrate the usage of :mod:`qtinter`.
For each example, the source code is listed, and the lines that demonstrate
the usage of :mod:`qtinter`'s API are highlighted.


.. _color-example:

Color Chooser
-------------

This example implements a command-line utility that displays the RGB value
of a color chosen by the user from a color dialog.

It demonstrates the use of :func:`using_qt_from_asyncio` to add Qt support
to an asyncio-based program.

Sample output:

.. code-block:: console

   $ python color.py
   #ff8655

Source code (``examples/color.py``):

.. literalinclude:: ../examples/color.py
   :language: python
   :emphasize-lines: 5,20
   :linenos:


.. _clock-example:

Digital Clock
-------------

This example displays an LCD-style digital clock.

It demonstrates the use of :func:`using_asyncio_from_qt` to add
asyncio support to a Qt application.

Sample screenshot:

.. image:: _static/clock.png
   :scale: 50%

Source code (``examples/clock.py``):

.. literalinclude:: ../examples/clock.py
   :language: python
   :emphasize-lines: 5,32
   :linenos:


.. _http-client-example:

Http Client
-----------

This example shows how to download a web page asynchronously using the
``httpx`` module and optionally cancel the download.

.. image:: _static/http_client.gif

Source code:

.. toggle::

   .. literalinclude:: ../examples/http_client.py
      :language: python
      :emphasize-lines: 4,68,218
      :linenos:


.. _read-out-example:

Read Out
--------

.. _QtTextToSpeech: https://doc-snapshots.qt.io/qt6-dev/qttexttospeech-index.html

.. _say: https://ss64.com/osx/say.html

This example implements a command line utility that reads out the text
from standard input.  It is a cross-platform version of the macOS `say`_
command.

The example demonstrates the use of :func:`using_qt_from_asyncio` to
use a Qt component (`QtTextToSpeech`_) in asyncio-driven code, and the
use of :func:`asyncsignal` to wait for a Qt signal.

.. note::

   On Unix, press ``Ctrl+D`` to terminate input.  On Windows, press ``Ctrl+Z``.

Sample output (on macOS 12):

.. code-block:: console

   $ python read_out.py -h
   usage: read_out.py [options]
   Read out text from stdin.
   Options:
       -e          Echo each line before reading it out
       -h          Show this screen and exit
       -l locale   One of en_US, fr_FR (default: en_US)
       -p pitch    Number between -1.0 and +1.0 (default: 0.0)
       -r rate     Number between -1.0 and +1.0 (default: 0.0)
       -v voice    One of Alex, Fiona, Fred, Samantha, Victoria (default: Alex)

Source code:

.. literalinclude:: ../examples/read_out.py
   :language: python
   :emphasize-lines: 6,22,77
   :linenos:


.. _where-am-i-example:

Where am I
----------

.. _QtPositioning: https://doc-snapshots.qt.io/qt6-dev/qtpositioning-index.html

This example implements a command line utility that prints the current
geolocation.

It demonstrates the use of :func:`using_qt_from_asyncio` to use
a Qt component (`QtPositioning`_) in asyncio-driven code.
It also demonstrates the use of :func:`asyncsignal` and
:func:`multisignal` to wait for the first of multiple Qt signals.

Sample output:

.. code-block:: console

   $ python where_am_i.py
   12° 34' 56.7" N, 98° 76' 54.3" E, 123.456m

Source code:

.. literalinclude:: ../examples/where_am_i.py
   :language: python
   :emphasize-lines: 5,23,42
   :linenos:


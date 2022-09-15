""" http_example.py - asynchronous http download and cancellation

This example displays a window that allows the user to download a web
page asynchronously and optionally cancel the download.

The window contains an 'Async GET' button whose 'clicked' signal is
connected to a coroutine function wrapped by asyncslot.asyncSlot.  The
window also contains a 'Cancel' button used to cancel the asynchronous
download operation.

To simulate slow network response so that it's easier to visualize the
difference between synchronous and asynchronous download, this example
implements a minimal http server that sleeps for 3 seconds before sending
back the response.  The http server runs in a separate thread and does
not use any of asyncslot's functionality.

Pay attention to code blocks marked with FEATURE -- they demonstrate the
usage of asyncslot.  The rest code builds up the GUI and program logic
and is not specific to asyncslot.
"""

import asyncio
import asyncslot
import sys
import time
from PyQt6 import QtWidgets
from bouncingwidget import BouncingWidget
from typing import Optional
import requests
import http.server
import threading
import httpx


def create_http_server():
    """ Create a local http server to simulate slow response """

    class MyRequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(3)  # simulate slow response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            content = f"You requested {self.path}".encode("utf-8")
            self.wfile.write(content)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                             MyRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    return server


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("asyncslot - Http Example")

        # Show a bouncing ball to visualize whether the Qt event loop is
        # blocked -- the ball freezes if the Qt event loop is blocked.
        self._bouncer = BouncingWidget()

        # URl input.
        self._url = QtWidgets.QLineEdit(self)

        # The 'Sync GET' button downloads the web page synchronously,
        # which blocks the Qt event loop.  The bouncing ball freezes
        # when this button is clicked until download is complete.
        self._sync_button = QtWidgets.QPushButton("Sync GET")
        self._sync_button.clicked.connect(self.sync_download)

        # The 'Async GET' button downloads the web page asynchronously.
        # The ball keeps bouncing while the download is in progress.
        self._async_button = QtWidgets.QPushButton("Async GET")

        # ---- FEATURE ----
        # To connect an async function to the clicked signal, wrap the async
        # function in asyncslot.asyncSlot.
        self._async_button.clicked.connect(
            asyncslot.asyncSlot(self.async_download))

        # ---- FEATURE ----
        # When an async download is in progress, _async_task is set to the
        # task executing the download, so that the download may be cancelled
        # by clicking the 'Cancel' button.
        self._async_task: Optional[asyncio.Task] = None

        # The 'Cancel' button is enabled when async download is in progress.
        self._cancel_button = QtWidgets.QPushButton("Cancel")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self.cancel_async_download)

        # Response from the http server is shown in the below box.
        self._output = QtWidgets.QTextEdit(self)

        # Set up layout.
        self._buttons = QtWidgets.QHBoxLayout()
        self._buttons.addWidget(self._sync_button)
        self._buttons.addWidget(self._async_button)
        self._buttons.addWidget(self._cancel_button)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.addWidget(self._bouncer)
        self._layout.addWidget(self._url)
        self._layout.addLayout(self._buttons)
        self._layout.addWidget(self._output)

        # Start a local HTTP server to simulate slow response.  The server
        # runs in a separate thread.
        self._server = create_http_server()

        # Set default URL to the locally-run http server, which sleeps for
        # 3 seconds before sending back a response.
        self._url.setText("http://{}:{}/dummy"
                          .format(*self._server.server_address))

    def closeEvent(self, event):
        # Handle the closeEvent to shut down the local HTTP server so that
        # the program exits (cleanly).  The shutdown() call blocks; you
        # may notice a short freeze of the bouncing ball.
        self._server.shutdown()
        event.accept()

    def sync_download(self):
        # When the 'Sync GET' button is clicked, download the web page
        # using the (blocking) requests library.  The bouncing ball freezes
        # until download is complete.  There is no need to disable buttons
        # etc because there is no chance for the Qt event loop to process
        # events or repaint the GUI.
        url = self._url.text() + "?sync"
        response = requests.get(url)
        self._output.setText(response.text)

    # ---- FEATURE ----
    # When the 'Async GET' button is clicked, initiate asynchronous download.
    async def async_download(self):
        # Retrieve and store the asyncio task wrapping this coroutine,
        # so that it may be cancelled by calling its cancel() method.
        self._async_task = asyncio.current_task()
        assert self._async_task is not None

        # Update GUI elements -- this is a common pattern in event handling.
        # Because asyncslot executes the slot immediately until the first
        # yield, the changes take effect immediately, eliminating potential
        # race conditions.  The actual GUI repainting happens after the first
        # yield, where control is given back to the Qt event loop.
        self._sync_button.setEnabled(False)
        self._async_button.setEnabled(False)
        self._cancel_button.setEnabled(True)
        self._output.clear()
        self._output.setEnabled(False)

        try:
            # Download web page using httpx library.  The httpx library
            # works with both asyncio and trio, and uses anyio to detect
            # the type of the running event loop.  That httpx works with
            # asyncslot shows that asyncslot's event loop behaves like
            # an asyncio event loop.
            async with httpx.AsyncClient() as client:
                url = self._url.text() + "?async"
                response = await client.get(url)
                # TODO: test asyncgen close
                body = await response.aread()
                self._output.setText(body.decode("utf-8"))

        except asyncio.CancelledError:
            # Catching a CancelledError indicates the task is cancelled.
            # This can happen either because the user clicked the 'Cancel'
            # button, or because the window is closed.  In the latter case
            # Qt's event loop exits and AsyncSlotRunner shuts down the
            # asyncslot event loop, cancelling all running tasks.
            if self.isVisible():
                # If the window is still open, the task must have been
                # cancelled by clicking the 'Cancel' button.  This is
                # because asyncslot only cancels running tasks _after_ the
                # Qt event loop exits, and the Qt event loop exits only
                # after all windows are closed.
                QtWidgets.QMessageBox.information(
                    self, "Note", "Download cancelled by user!")
            else:
                # Do nothing if user closed the window.
                pass

        finally:
            # Restore GUI element states.
            self._output.setEnabled(True)
            self._cancel_button.setEnabled(False)
            self._async_button.setEnabled(True)
            self._sync_button.setEnabled(True)
            self._async_task = None

    # ---- FEATURE ----
    # When the 'Cancel' button is clicked, cancel the async download.
    def cancel_async_download(self):
        # The 'Cancel' button is enabled only if the async download is
        # in progress, so the task object must be set.
        assert self._async_task is not None

        # Initiate cancellation request.  This throws asyncio.CancelledError
        # into the (suspended) coroutine, which must catch the exception and
        # perform actual cancellation.  (Note that it is possible for the
        # task to be done before CancelledError is thrown, as a cancellation
        # request is scheduled by call_soon and it could happen that
        # a task completion callback is scheduled before it.)  Cancelling
        # a done task has no effect.
        self._async_task.cancel()


def main():
    # Create a QApplication instance, as usual.
    app = QtWidgets.QApplication([])

    # Create widgets, as usual.
    widget = MyWidget()
    widget.resize(400, 300)
    widget.show()

    # ---- FEATURE ----
    # For asyncslot to work, enclose app.exec inside the context manager
    # AsyncSlotRunner().  The runner is responsible for starting up and
    # shutting down the logical asyncio event loop.
    with asyncslot.AsyncSlotRunner():
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

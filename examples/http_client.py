"""Demo asyncio http download and cancellation from Qt app."""

import asyncio
import qtinter
import sys
import time
from PyQt6 import QtCore, QtWidgets
from typing import Optional
import requests
import http.server
import threading
import httpx


def create_http_server():
    """Create a minimal local http server.

    This server sleeps for 3 seconds before sending back a response.
    This makes it easier to visualize the difference between synchronous
    and asynchronous download.

    The server implementation is unrelated to qtinter.
    """
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

        self.setWindowTitle("qtinter - Http Client Example")

        # Show an indefinite progress bar to visualize whether the Qt event
        # loop is blocked -- the progress bar freezes if the Qt event loop
        # is blocked.
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 0)

        # URL input.
        self._url = QtWidgets.QLineEdit(self)

        # The 'Sync GET' button downloads the web page synchronously,
        # which blocks the Qt event loop.  The progress bar freezes
        # when this button is clicked until the download completes.
        self._sync_button = QtWidgets.QPushButton("Sync GET")
        self._sync_button.clicked.connect(self.sync_download)

        # The 'Async GET' button downloads the web page asynchronously.
        # The progress bar keeps running while the download is in progress.
        self._async_button = QtWidgets.QPushButton("Async GET")

        # [DEMO] To connect an async function to the clicked signal, wrap
        # the async function with qtinter.asyncslot.
        self._async_button.clicked.connect(
            qtinter.asyncslot(self.async_download))

        # [DEMO] When an async download is in progress, _async_task is set
        # to the task executing the download, so that it may be cancelled
        # by clicking the 'Cancel' button.
        self._async_task: Optional[asyncio.Task] = None

        # The 'Cancel' button is enabled when async download is in progress.
        self._cancel_button = QtWidgets.QPushButton("Cancel")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self.cancel_async_download)

        # Response from the http server is shown in the below box.
        self._output = QtWidgets.QTextEdit(self)
        self._output.setReadOnly(True)

        # Set up layout.
        self._buttons = QtWidgets.QHBoxLayout()
        self._buttons.setContentsMargins(0, 0, 0, 0)
        self._buttons.setSpacing(5)
        self._buttons.addWidget(self._sync_button)
        self._buttons.addWidget(self._async_button)
        self._buttons.addWidget(self._cancel_button)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(5)
        self._layout.addWidget(self._progress)
        self._layout.addWidget(self._url)
        self._layout.addLayout(self._buttons)
        self._layout.addWidget(self._output)

        # Start a local HTTP server to simulate slow response.  The server
        # runs in a separate thread.
        self._server = create_http_server()

        # Set default URL to the locally-run http server.
        self._url.setText("http://{}:{}/dummy"
                          .format(*self._server.server_address))

    def closeEvent(self, event):
        # Handle the closeEvent to shut down the local HTTP server so that
        # the program exits (cleanly).  The shutdown() call blocks; you
        # might observe a short freeze of the progress bar.
        self._server.shutdown()
        event.accept()

    def sync_download(self):
        # When the 'Sync GET' button is clicked, download the web page
        # using the (blocking) requests library.  This has two drawbacks:
        # 1. The GUI freezes during the download.  For example, the progress
        #    bar stops updating.
        # 2. Buttons remain clickable even if disabled before download starts
        #    and re-enabled after download completes.  A workaround seems to
        #    be waiting for 10 milliseconds before re-enabling the button;
        #    hard-coding a timeout is certainly not ideal.
        url = self._url.text()
        self._async_button.setEnabled(False)
        try:
            response = requests.get(url)
            self._output.setText(response.text)
        finally:
            QtCore.QTimer.singleShot(
                10, lambda: self._async_button.setEnabled(True))

    # [DEMO] asynchronous slot for the 'Async GET' button.
    async def async_download(self):
        # Store the asyncio task wrapping the running coroutine so that
        # it may be cancelled by calling its cancel() method.
        self._async_task = asyncio.current_task()
        assert self._async_task is not None

        # Update GUI elements -- this is a common pattern in event handling.
        # Because qtinter.asyncslot() executes the coroutine immediately
        # until the first yield, the changes take effect immediately,
        # eliminating potential race conditions.  The actual GUI repainting
        # happens after the first yield when control is returned to the Qt
        # event loop.
        self._sync_button.setEnabled(False)
        self._async_button.setEnabled(False)
        self._cancel_button.setEnabled(True)
        self._output.clear()

        try:
            # Download web page using httpx library.  The httpx library
            # works with both asyncio and trio, and uses anyio to detect
            # the type of the running event loop.  That httpx works with
            # qtinter shows that qtinter's event loop behaves like
            # an asyncio event loop.
            async with httpx.AsyncClient() as client:
                url = self._url.text()
                response = await client.get(url)
                # TODO: test asyncgen close
                body = await response.aread()
                self._output.setText(body.decode("utf-8"))

        except asyncio.CancelledError:
            # Catching a CancelledError indicates the task is cancelled.
            # This can happen either because the user clicked the 'Cancel'
            # button, or because the window is closed.  In the latter case
            # Qt's event loop exits and qtinter.using_asyncio_from_qt()
            # shuts down qtinter's event loop after cancelling all pending
            # tasks.
            if self.isVisible():
                # If the window is still open, the task must have been
                # cancelled by clicking the 'Cancel' button.  This is
                # because qtinter only cancels pending tasks _after_ the
                # Qt event loop exits, and the Qt event loop exits only
                # after all windows are closed.
                QtWidgets.QMessageBox.information(
                    self, "Note", "Download cancelled by user!")
            else:
                # Do nothing if user closed the window.
                pass

        finally:
            # Restore GUI element states.
            self._cancel_button.setEnabled(False)
            self._async_button.setEnabled(True)
            self._sync_button.setEnabled(True)
            self._async_task = None

    # [DEMO] When the 'Cancel' button is clicked, cancel the async download.
    def cancel_async_download(self):
        # The 'Cancel' button is enabled only if the async download is
        # in progress, so the task object must be set.
        assert self._async_task is not None

        # Initiate cancellation request.  This throws asyncio.CancelledError
        # into the (suspended) coroutine, which must catch the exception and
        # perform actual cancellation.  (Note that it is possible for the
        # task to be done before CancelledError is thrown, as a cancellation
        # request is scheduled by call_soon() and it might so happen that
        # a task completion callback is scheduled before it.)  Cancelling
        # a done task has no effect.
        self._async_task.cancel()


def main():
    # Create a QApplication instance, as usual.
    app = QtWidgets.QApplication([])

    # Create widgets, as usual.
    widget = MyWidget()
    widget.resize(400, 200)
    widget.show()

    # [DEMO] To enable asyncio-based components from Qt-driven code,
    # enclose app.exec() inside the qtinter.using_asyncio_from_qt()
    # context manager.  This context manager takes care of starting
    # up and shutting down an asyncio-compatible logical event loop.
    with qtinter.using_asyncio_from_qt():
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

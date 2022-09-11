""" http_example.py - simple GUI to download a web page """

import asyncio
import sys
import time
from PyQt6 import QtWidgets
from bouncingwidget import BouncingWidget
from typing import Optional
import asyncslot
import requests
import http.server
import threading
import httpx


def create_http_server():
    """ Create a local http server to simulate slow response """

    class MyRequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(5)  # simulate slow response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"You requested {self.path}".encode("utf-8"))

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 12345),
                                             MyRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    return server


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Http Example")

        self._bouncer = BouncingWidget()

        self._url = QtWidgets.QLineEdit(self)
        self._url.setText("http://127.0.0.1:12345/dummy")

        self._sync_button = QtWidgets.QPushButton("Sync GET")
        self._async_button = QtWidgets.QPushButton("Async GET")
        self._cancel_button = QtWidgets.QPushButton("Cancel")
        self._cancel_button.setEnabled(False)

        self._output = QtWidgets.QTextEdit(self)

        self._buttons = QtWidgets.QHBoxLayout()
        self._buttons.addWidget(self._sync_button)
        self._buttons.addWidget(self._async_button)
        self._buttons.addWidget(self._cancel_button)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.addWidget(self._bouncer)
        self._layout.addWidget(self._url)
        self._layout.addLayout(self._buttons)
        self._layout.addWidget(self._output)

        self._sync_button.clicked.connect(self.sync_download)
        self._async_button.clicked.connect(
            asyncslot.asyncSlot(self.async_download))
        self._cancel_button.clicked.connect(self.cancel_async_download)

        self._server = create_http_server()
        self._async_task: Optional[asyncio.Task] = None

    def closeEvent(self, event):
        self._server.shutdown()  # blocks
        event.accept()

    def sync_download(self):
        url = self._url.text() + "?sync"
        response = requests.get(url)
        self._output.setText(response.text)

    async def async_download(self):
        assert self._async_task is None
        self._async_task = asyncio.current_task()
        assert self._async_task is not None

        self._sync_button.setEnabled(False)
        self._async_button.setEnabled(False)
        self._cancel_button.setEnabled(True)
        self._output.clear()
        self._output.setEnabled(False)

        try:
            async with httpx.AsyncClient() as client:
                url = self._url.text() + "?async"
                response = await client.get(url)
                body = await response.aread()
                text = body.decode("utf-8")
                self._output.setText(text)
        except asyncio.CancelledError:
            if self.isVisible():  # cancelled by Cancel button
                QtWidgets.QMessageBox.information(
                    self, "Note", "Download cancelled by user!")
            else:  # cancelled due to Window close
                pass
        finally:
            self._output.setEnabled(True)
            self._cancel_button.setEnabled(False)
            self._async_button.setEnabled(True)
            self._sync_button.setEnabled(True)
            self._async_task = None

    def cancel_async_download(self):
        if self._async_task is not None:
            self._async_task.cancel()


def main():
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(400, 300)
    widget.show()

    with asyncslot.AsyncSlotRunner():
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

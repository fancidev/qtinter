""" sleep_example.py - simple GUI to test async slot """

import asyncio
import qtinter
import sys
import time
from PyQt6 import QtWidgets
from bouncingwidget import BouncingWidget
import traceback


def wrap(fn):
    def call(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        except BaseException as exc:
            print(traceback.format_exc(), file=sys.stderr)
            raise
    return call


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("qtinter - sleep example")

        self._layout = QtWidgets.QVBoxLayout(self)
        self._bouncer = BouncingWidget()
        self._layout.addWidget(self._bouncer)
        self._button_group = QtWidgets.QHBoxLayout()
        self._sync_button = QtWidgets.QPushButton("Sync Sleep")
        self._async_button = QtWidgets.QPushButton("Async Sleep")
        self._button_group.addWidget(self._sync_button)
        self._button_group.addWidget(self._async_button)
        self._layout.addLayout(self._button_group)

        self._sync_button.clicked.connect(self.sync_sleep)
        self._async_button.clicked.connect(qtinter.asyncslot(self.async_sleep))

    def sync_sleep(self):
        time.sleep(3)
        QtWidgets.QMessageBox.information(self, 'Test', 'Done')

    async def async_sleep(self, checked):
        self._async_button.setEnabled(False)
        await asyncio.sleep(3)
        QtWidgets.QMessageBox.information(self, 'Test', 'Done')
        self._async_button.setEnabled(True)


def main():
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(400, 300)
    widget.show()

    with qtinter.using_asyncio_from_qt():
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

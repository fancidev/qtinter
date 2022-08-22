""" testwindow.py - simple GUI to test async slot """

import sys
import time
from PySide6 import QtCore, QtWidgets
from bouncingwidget import BouncingWidget


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AsyncSlot Test")

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
        self._async_button.clicked.connect(self.async_sleep)

    @QtCore.Slot()
    def sync_sleep(self):
        time.sleep(3)

    @QtCore.Slot()
    def async_sleep(self):
        raise NotImplementedError


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(400, 300)
    widget.show()

    sys.exit(app.exec())

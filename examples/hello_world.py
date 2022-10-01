"""Basic demo using asyncio from Qt application"""

import asyncio
import qtinter
from PyQt6 import QtCore, QtWidgets


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._label = QtWidgets.QLabel()
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setWindowTitle("qtinter - Hello World Example")
        self.setCentralWidget(self._label)
        QtCore.QTimer.singleShot(0, qtinter.asyncslot(self.hello_world))

    async def hello_world(self):
        text = "HELLO WORLD"
        while True:
            for n in range(len(text)):
                self._label.setText(text[:n])
                await asyncio.sleep(0.1)
            for n in range(len(text)):
                self._label.setText(text[n:])
                await asyncio.sleep(0.1)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MyWindow()
    window.resize(300, 50)
    window.show()
    with qtinter.using_asyncio_from_qt():
        app.exec()

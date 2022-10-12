"""Display LCD-style digital clock"""

import asyncio
import datetime
import qtinter
from PyQt6 import QtCore, QtWidgets


class MyWidget(QtWidgets.QLCDNumber):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("qtinter - LCD Clock Example")
        self.setNumDigits(8)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(qtinter.asyncslot(self.tick))
        timer.setSingleShot(True)
        timer.start(0)

    async def tick(self):
        while True:
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            self.display(time_str)
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MyWidget()
    window.resize(300, 50)
    window.show()
    with qtinter.using_asyncio_from_qt():
        app.exec()

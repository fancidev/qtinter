"""Display LCD-style digital clock"""

import asyncio
import datetime
import qtinter  # <-- import module
from PySide6 import QtWidgets

class Clock(QtWidgets.QLCDNumber):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDigitCount(8)

    def showEvent(self, event):
        self._task = asyncio.create_task(self._tick())

    def hideEvent(self, event):
        self._task.cancel()

    async def _tick(self):
        while True:
            t = datetime.datetime.now()
            self.display(t.strftime("%H:%M:%S"))
            await asyncio.sleep(1.0 - t.microsecond / 1000000 + 0.05)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Clock()
    widget.setWindowTitle("qtinter - Digital Clock example")
    widget.resize(300, 50)

    with qtinter.using_asyncio_from_qt():  # <-- enable asyncio in qt code
        widget.show()
        app.exec()

"""Display LCD-style digital clock"""

import asyncio
import datetime
import qtinter  # <-- import module
from PyQt6 import QtCore, QtWidgets


async def tick():
    while True:
        widget.display(datetime.datetime.now().strftime("%H:%M:%S"))
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = QtWidgets.QLCDNumber()
    widget.setWindowTitle("qtinter - LCD Clock Example")
    widget.setNumDigits(8)
    widget.resize(300, 50)
    widget.show()

    timer = QtCore.QTimer(widget)
    timer.timeout.connect(qtinter.asyncslot(tick))  # <-- wrap in asyncslot
    timer.setSingleShot(True)
    timer.start(0)

    with qtinter.using_asyncio_from_qt():  # <-- enclose in context manager
        app.exec()

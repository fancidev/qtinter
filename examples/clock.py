"""Display LCD-style digital clock"""

import asyncio
import datetime
import qtinter  # <-- import module
from PySide6 import QtWidgets


async def tick():
    while True:
        widget.display(datetime.datetime.now().strftime("%H:%M:%S"))
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = QtWidgets.QLCDNumber()
    widget.setDigitCount(8)
    widget.setWindowTitle("qtinter - Digital Clock example")
    widget.resize(300, 50)
    widget.show()

    with qtinter.using_asyncio_from_qt():  # <-- enable asyncio in qt code
        task = asyncio.create_task(tick())
        app.exec()

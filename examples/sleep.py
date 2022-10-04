"""Minimal demo using asyncio from Qt for Python"""

import asyncio
import qtinter  # <-- import module
from PyQt6 import QtWidgets


async def sleep():
    button.setEnabled(False)
    await asyncio.sleep(1)
    button.setEnabled(True)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    button = QtWidgets.QPushButton()
    button.setText('Sleep for one second')
    button.clicked.connect(qtinter.asyncslot(sleep))  # <-- wrap coroutine function
    button.show()

    with qtinter.using_asyncio_from_qt():  # <-- enclose in context manager
        app.exec()

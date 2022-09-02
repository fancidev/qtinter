""" minimal_gui.py - minimal gui application using asyncslot """

import asyncio
from PySide6 import QtWidgets
from asyncslot import asyncSlot, AsyncSlotRunner


async def say_hi():
    await asyncio.sleep(1)
    QtWidgets.QMessageBox.information(None, "Demo", "Hi")


if __name__ == '__main__':
    app = QtWidgets.QApplication()

    button = QtWidgets.QPushButton()
    button.setText('Say Hi after one second')
    button.clicked.connect(asyncSlot(say_hi))
    button.show()

    with AsyncSlotRunner():
        app.exec()

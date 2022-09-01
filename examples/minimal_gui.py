""" minimal_gui.py - minimal gui application using asyncslot """

import asyncio
from PySide6 import QtWidgets
from asyncslot import AsyncSlot, install_event_loop


@AsyncSlot()
async def say_hi():
    await asyncio.sleep(1)
    QtWidgets.QMessageBox.information(None, "Demo", "Hi")


if __name__ == '__main__':
    app = QtWidgets.QApplication()

    button = QtWidgets.QPushButton()
    button.setText('Say Hi after one second')
    button.clicked.connect(say_hi)
    button.show()

    with install_event_loop():
        app.exec()

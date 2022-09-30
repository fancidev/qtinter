""" minimal_gui.py - minimal gui application using asyncslot """

import asyncio
import qtinter  # <-- import module
from PyQt6 import QtWidgets


async def say_hi():
    await asyncio.sleep(1)
    QtWidgets.QMessageBox.information(None, "Demo", "Hi")

app = QtWidgets.QApplication([])

button = QtWidgets.QPushButton()
button.setText('Say Hi in one second')
button.clicked.connect(qtinter.asyncslot(say_hi))  # <-- wrap coroutine function
button.show()

with qtinter.using_asyncio_from_qt():  # <-- enclose app.exec in context manager
    app.exec()

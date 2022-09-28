""" minimal_gui.py - minimal gui application using asyncslot """

import asyncio
import qtinter  # <-- step 1 - import module
from PyQt6 import QtWidgets


async def say_hi():
    await asyncio.sleep(1)
    QtWidgets.QMessageBox.information(None, "Demo", "Hi")

app = QtWidgets.QApplication([])

button = QtWidgets.QPushButton()
button.setText('Say Hi in one second')
button.clicked.connect(qtinter.asyncslot(say_hi))  # <-- step 3 - wrap slot
button.show()

with qtinter.QiRunner():  # <-- step 2 - enclose in context manager
    app.exec()

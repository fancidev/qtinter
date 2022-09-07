""" gui_test_clicked.py - test asyncSlot with QAbstractButton """

import asyncio
from shim import QtCore, QtWidgets
from asyncslot import asyncSlot, AsyncSlotRunner


async def quit_later():
    await asyncio.sleep(0)
    QtWidgets.QApplication.quit()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    button = QtWidgets.QPushButton()
    button.setText('Quit')
    button.clicked.connect(asyncSlot(quit_later))
    button.show()

    timer = QtCore.QTimer()
    timer.timeout.connect(button.click)
    timer.start()

    with AsyncSlotRunner():
        if hasattr(app, 'exec'):
            app.exec()
        else:
            app.exec_()

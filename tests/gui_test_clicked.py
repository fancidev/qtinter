""" gui_test_clicked.py - test asyncSlot with QAbstractButton """

import asyncio
from shim import QtCore, QtWidgets
from qtinter import asyncslot, QiRunner


async def quit_later():
    await asyncio.sleep(0)
    QtWidgets.QApplication.quit()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    button = QtWidgets.QPushButton()
    button.setText('Quit')
    button.clicked.connect(asyncslot(quit_later))
    button.show()

    timer = QtCore.QTimer()
    timer.timeout.connect(button.click)
    timer.start()

    with QiRunner():
        if hasattr(app, 'exec'):
            app.exec()
        else:
            app.exec_()

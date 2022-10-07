""" gui_test_clicked.py - test qtinter with QAbstractButton """

import asyncio
import qtinter
from shim import QtCore, QtWidgets


async def quit_later():
    await asyncio.sleep(0)
    QtWidgets.QApplication.quit()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    button = QtWidgets.QPushButton()
    button.setText('Quit')
    button.clicked.connect(qtinter.asyncslot(quit_later))
    button.show()

    timer = QtCore.QTimer()
    timer.timeout.connect(button.click)
    timer.start()

    with qtinter.using_asyncio_from_qt():
        if hasattr(app, 'exec'):
            app.exec()
        else:
            app.exec_()

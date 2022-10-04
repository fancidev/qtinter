"""Minimal demo using Qt from asyncio code"""

import asyncio
import qtinter  # <-- import module
from PyQt6 import QtWidgets


async def choose_color():
    dialog = QtWidgets.QColorDialog()
    dialog.show()
    result = await qtinter.asyncsignal(dialog.finished)  # <-- wait for signal
    if result == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.selectedColor().name()
    else:
        return None


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    with qtinter.using_qt_from_asyncio():  # <-- enclose in context manager
        color = asyncio.run(choose_color())
        if color is not None:
            print(color)

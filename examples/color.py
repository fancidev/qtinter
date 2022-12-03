"""Display the RGB code of a color chosen by the user"""

import asyncio
import qtinter  # <-- import module
from PySide6 import QtWidgets

async def choose_color():
    dialog = QtWidgets.QColorDialog()
    dialog.show()
    future = asyncio.Future()
    dialog.finished.connect(future.set_result)
    result = await future
    if result == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.selectedColor().name()
    else:
        return None

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    with qtinter.using_qt_from_asyncio():  # <-- enable qt in asyncio code
        color = asyncio.run(choose_color())
        if color is not None:
            print(color)

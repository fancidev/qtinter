# qtinter — Interop between asyncio and Qt for Python

[![codecov](https://codecov.io/gh/fancidev/qtinter/branch/master/graph/badge.svg?token=JZ5ON6CHKA)](https://codecov.io/gh/fancidev/qtinter)
[![docs](https://readthedocs.org/projects/qtinter/badge/?version=latest)](https://qtinter.readthedocs.io/en/latest/?badge=latest)
[![tests](https://github.com/fancidev/qtinter/actions/workflows/tests.yml/badge.svg)](https://github.com/fancidev/qtinter/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/qtinter)](https://pypi.org/project/qtinter/)

`qtinter` is a Python module that brings together asyncio and Qt
for Python, allowing you to use one from the other seamlessly.

Read the [full documentation](https://qtinter.readthedocs.io) or check out the quickstart below.

## Installation

```commandline
$ pip install qtinter
```

## Using asyncio from Qt

To use asyncio-based libraries in Qt for Python, enclose `app.exec()`
inside context manager `qtinter.using_asyncio_from_qt()`.

Minimal example (taken from `examples/clock.py`):

```Python
"""Display LCD-style digital clock"""

import asyncio
import datetime
import qtinter  # <-- import module
from PySide6 import QtWidgets

async def tick():
    while True:
        widget.display(datetime.datetime.now().strftime("%H:%M:%S"))
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = QtWidgets.QLCDNumber()
    widget.setDigitCount(8)
    widget.setWindowTitle("qtinter - Digital Clock example")
    widget.resize(300, 50)
    widget.show()

    with qtinter.using_asyncio_from_qt():  # <-- enable asyncio in qt code
        task = asyncio.create_task(tick())
        app.exec()
```

## Using Qt from asyncio

To use Qt components from asyncio-based code, enclose the asyncio
entry-point inside context manager `qtinter.using_qt_from_asyncio()`.

Minimal example (taken from `examples/color.py`):

```Python
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
```

## Using modal dialogs

To execute a modal dialog without blocking the asyncio event loop,
wrap the dialog entry-point in `qtinter.modal()` and `await` on it.

Minimal example (taken from `examples/hit_100.py`):

```Python
import asyncio
import qtinter
from PySide6 import QtWidgets

async def main():
    async def counter():
        nonlocal n
        while True:
            print(f"\r{n}", end='', flush=True)
            await asyncio.sleep(0.025)
            n += 1

    n = 0
    counter_task = asyncio.create_task(counter())
    await qtinter.modal(QtWidgets.QMessageBox.information)(
        None, "Hit 100", "Click OK when you think you hit 100.")
    counter_task.cancel()
    if n == 100:
        print("\nYou did it!")
    else:
        print("\nTry again!")

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    with qtinter.using_qt_from_asyncio():
        asyncio.run(main())
```


## Requirements

`qtinter` supports the following:

- Python version: 3.7 or higher
- Qt binding: PyQt5, PyQt6, PySide2, PySide6
- Operating system: Linux, MacOS, Windows


## License

BSD License.


## Contributing

Please raise an issue if you have any questions. Pull requests are more
than welcome!


## Credits

`qtinter` is derived from
[qasync](https://github.com/CabbageDevelopment/qasync) but rewritten from 
scratch.  qasync is derived from 
[asyncqt](https://github.com/gmarull/asyncqt), which is derived from
[quamash](https://github.com/harvimt/quamash).

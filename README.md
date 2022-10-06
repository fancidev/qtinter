# qtinter — Interop between asyncio and Qt for Python

[![build](https://github.com/fancidev/qtinter/actions/workflows/build.yml/badge.svg)](https://github.com/fancidev/qtinter/actions/workflows/build.yml)
[![docs](https://readthedocs.org/projects/qtinter/badge/?version=latest)](https://qtinter.readthedocs.io/en/latest/?badge=latest)
[![tests](https://github.com/fancidev/qtinter/actions/workflows/tests.yml/badge.svg)](https://github.com/fancidev/qtinter/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/fancidev/qtinter/branch/master/graph/badge.svg?token=JZ5ON6CHKA)](https://codecov.io/gh/fancidev/qtinter)
[![PyPI](https://img.shields.io/pypi/v/qtinter)](https://pypi.org/project/qtinter/)

`qtinter` is a Python module that brings together asyncio and Qt
for Python, allowing you to use one from the other seamlessly.

## Quickstart

### Installation

```commandline
$ pip install qtinter
```

### Using asyncio from Qt

To use asyncio-based libraries in Qt for Python, enclose `app.exec()`
inside context manager `qtinter.using_asyncio_from_qt()`, and optionally
connect Qt signals to coroutine functions using `qtinter.asyncslot()`.

Minimal example (taken from `examples/sleep.py`):

```Python
import asyncio
import qtinter  # <-- import module
from PyQt6 import QtWidgets

async def sleep():
    button.setEnabled(False)
    await asyncio.sleep(1)
    button.setEnabled(True)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    button = QtWidgets.QPushButton()
    button.setText('Sleep for one second')
    button.clicked.connect(qtinter.asyncslot(sleep))  # <-- wrap coroutine function
    button.show()

    with qtinter.using_asyncio_from_qt():  # <-- enclose in context manager
        app.exec()
```

### Using Qt from asyncio

To use Qt components from asyncio-based code, enclose the asyncio
entry-point inside context manager `qtinter.using_qt_from_asyncio()`,
and optionally wait for Qt signals using `qtinter.asyncsignal()`.

Minimal example (taken from `examples/color.py`):

```Python
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
```

## Documentation

See full documentation at [qtinter.readthedocs.io](https://qtinter.readthedocs.io).


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

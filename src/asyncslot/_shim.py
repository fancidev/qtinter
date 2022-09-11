""" _shim.py - common imports for PyQt5, PyQt6, PySide2, PySide6 """

import sys


__all__ = 'QtCore',


if 'PyQt5' in sys.modules:
    from PyQt5 import QtCore
    QtCore.Signal = QtCore.pyqtSignal

elif 'PyQt6' in sys.modules:
    from PyQt6 import QtCore
    QtCore.Signal = QtCore.pyqtSignal

elif 'PySide2' in sys.modules:
    from PySide2 import QtCore

elif 'PySide6' in sys.modules:
    from PySide6 import QtCore

else:
    raise ImportError('One of PyQt5, PyQt6, PySide2 or PySide6 must be '
                      'imported before importing asyncslot')

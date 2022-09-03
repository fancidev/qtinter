""" shim.py - utility functions for testing """

import os


__all__ = 'QtCore',


qt_module_name = os.getenv("TEST_QT_MODULE", "").lower()

if qt_module_name == "pyqt5":
    from PyQt5 import QtCore

elif qt_module_name == "pyqt6":
    from PyQt6 import QtCore

elif qt_module_name == "pyside2":
    from PySide2 import QtCore

elif qt_module_name == "pyside6":
    from PySide6 import QtCore

else:
    raise ImportError(f"unsupported TEST_QT_MODULE: '{qt_module_name}'")

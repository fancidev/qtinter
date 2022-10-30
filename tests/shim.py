"""Test helper to import binding"""

import os


__all__ = ()


qt_module_name = os.getenv("TEST_QT_MODULE", "")
if qt_module_name == "":
    raise ImportError("environment variable TEST_QT_MODULE must be set")


if qt_module_name == "PyQt5":
    from PyQt5 import QtCore, QtWidgets

elif qt_module_name == "PyQt6":
    from PyQt6 import QtCore, QtWidgets

elif qt_module_name == "PySide2":
    from PySide2 import QtCore, QtWidgets

elif qt_module_name == "PySide6":
    from PySide6 import QtCore, QtWidgets

else:
    raise ImportError(f"unsupported TEST_QT_MODULE value: '{qt_module_name}'")

"""Test helper to import Qt binding defined by TEST_QT_MODULE environment
variable.  This script does not use qtinter functionality."""

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


is_pyqt = QtCore.__name__.startswith('PyQt')

if is_pyqt:
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
else:
    Signal = QtCore.Signal
    Slot = QtCore.Slot


def run_test_script(filename, *args, **env):
    from test.support.script_helper import run_python_until_end
    folder = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    env = {
        "__cwd": folder,
        "PYTHONPATH": "src",
        "COVERAGE_PROCESS_START": ".coveragerc",
        **env
    }

    result, cmd = run_python_until_end(
        os.path.join("tests", filename), *args, **env)
    return (
        result.rc,
        str(result.out, encoding="utf-8"),
        str(result.err, encoding="utf-8"),
    )

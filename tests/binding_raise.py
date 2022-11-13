"""Helper script used by binding_tests.py"""

import importlib
import sys

binding_name = sys.argv[1]
exception_name = sys.argv[2]
QtCore = importlib.import_module(f"{binding_name}.QtCore")
app = QtCore.QCoreApplication([])


def slot():
    exc = eval(exception_name)
    raise exc


QtCore.QTimer.singleShot(0, slot)
QtCore.QTimer.singleShot(0, app.quit)

if hasattr(app, "exec"):
    app.exec()
else:
    app.exec_()

print("post exec")

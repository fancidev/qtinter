"""Helper script used by test_events.py"""

import coverage
coverage.process_startup()

import asyncio
import qtinter
import sys
from qtinter.bindings import QtCore


def f():
    exception_name = sys.argv[1]
    raise eval(exception_name)


app = QtCore.QCoreApplication([])
QtCore.QTimer.singleShot(100, app.quit)
with qtinter.using_asyncio_from_qt():
    asyncio.get_running_loop().call_soon(f)
    if hasattr(app, "exec"):
        app.exec()
    else:
        app.exec_()

print("post exec")

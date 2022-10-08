""" bindings.py - resolve Python/Qt binding at run-time """

import os
import sys


__all__ = 'QtCore',


imported = []
for binding in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6'):
    if binding in sys.modules:
        imported.append(binding)


if len(imported) == 0:
    binding = os.getenv("QTINTERBINDING", "")
    if not binding:
        raise ImportError(
            'no Qt binding is imported and QTINTERBINDING is not set')

elif len(imported) == 1:
    binding = imported[0]

else:
    raise ImportError(f'more than one Qt bindings are imported: {imported}')


# Explicitly list the branches for coverage testing.
if binding == 'PyQt5':
    from PyQt5 import QtCore

elif binding == 'PyQt6':
    from PyQt6 import QtCore

elif binding == 'PySide2':
    from PySide2 import QtCore

elif binding == 'PySide6':
    from PySide6 import QtCore

else:
    raise ImportError(f"unsupported QTINTERBINDING value '{binding}'")


class _QiObjectImpl(QtCore.QObject):
    if hasattr(QtCore, "pyqtSignal"):
        qi_signal = QtCore.pyqtSignal()
    else:
        qi_signal = QtCore.Signal()

    def add_callback(self, callback):
        # Make queued connection to avoid re-entrance.
        self.qi_signal.connect(
            callback, QtCore.Qt.ConnectionType.QueuedConnection)

    def remove_callback(self, callback):
        self.qi_signal.disconnect(callback)

    def invoke_callbacks(self):
        self.qi_signal.emit()

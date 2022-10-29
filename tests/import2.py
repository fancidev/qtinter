"""Helper script used by test_import.py"""

import coverage
coverage.process_startup()

from qtinter.bindings import QtCore
print(QtCore.__name__)

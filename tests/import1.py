"""Helper script used by test_import.py"""

import coverage
coverage.process_startup()

import sys
import importlib

binding_name = sys.argv[1]
importlib.import_module(binding_name)

from qtinter.bindings import QtCore

print(QtCore.__name__)

"""Helper script used by test_import.py"""

import coverage
coverage.process_startup()

import importlib
import os
import sys

binding_name = os.getenv("QTINTERBINDING")

mod = importlib.import_module(binding_name)

sys.modules["PySide2"] = mod
sys.modules["PySide6"] = mod
sys.modules["PyQt5"] = mod
sys.modules["PyQt6"] = mod

from qtinter.bindings import QtCore

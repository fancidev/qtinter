"""Helper script used by test_import.py"""

import coverage
coverage.process_startup()

import asyncio
import sys
import importlib
import qtinter

binding_name = sys.argv[1]
mod = importlib.import_module(f"{binding_name}.QtCore")
app = mod.QCoreApplication([])


async def coro():
    from qtinter.bindings import QtCore
    print(QtCore.__name__)

with qtinter.using_qt_from_asyncio():
    asyncio.run(coro())

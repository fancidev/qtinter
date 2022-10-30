"""Helper script used by test_events.py"""

import coverage
coverage.process_startup()

import asyncio
import qtinter
from qtinter.bindings import QtCore


app = QtCore.QCoreApplication([])
QtCore.QCoreApplication.exit(0)


async def coro():
    pass

with qtinter.using_qt_from_asyncio():
    asyncio.run(coro())

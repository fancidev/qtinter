"""Helper script used by test_events.py"""

import coverage
coverage.process_startup()

import asyncio
import qtinter
from qtinter.bindings import QtCore


app = QtCore.QCoreApplication([])


async def coro():
    QtCore.QCoreApplication.exit(0)

with qtinter.using_qt_from_asyncio():
    asyncio.run(coro())

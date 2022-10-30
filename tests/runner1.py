"""Helper script used by test_events.py"""

import coverage
coverage.process_startup()

import asyncio
import qtinter


async def coro():
    pass

with qtinter.using_qt_from_asyncio():
    asyncio.run(coro())

"""Demonstrates asyncio.Runner usage"""

import asyncio
import datetime
import qtinter
import sys
from PySide6 import QtCore


if sys.version_info < (3, 11):
    raise RuntimeError("This example requires Python 3.11 or above")


async def coro():
    print("Press Ctrl+C to stop")
    timer = QtCore.QTimer()
    timer.setInterval(500)
    timer.start()
    while True:
        await qtinter.asyncsignal(timer.timeout)
        print(f"\r{datetime.datetime.now().strftime('%H:%M:%S')}", end="")


if __name__ == "__main__":
    app = QtCore.QCoreApplication([])
    with asyncio.Runner(loop_factory=qtinter.new_event_loop) as runner:
        runner.run(coro())

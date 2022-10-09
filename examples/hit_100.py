"""Demo non-blocking dialog exec"""

import asyncio
import qtinter
from PyQt6 import QtWidgets


async def main():
    async def counter():
        nonlocal n
        while True:
            print(f"\r{n}", end='', flush=True)
            await asyncio.sleep(0.025)
            n += 1

    n = 0
    counter_task = asyncio.create_task(counter())
    await qtinter.modal(QtWidgets.QMessageBox.information)(
        None, "Hit 100", "Click OK when you think you hit 100.")
    counter_task.cancel()
    if n == 100:
        print("\nYou did it!")
    else:
        print("\nTry again!")


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    with qtinter.using_qt_from_asyncio():
        asyncio.run(main())

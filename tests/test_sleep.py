import asyncio
from PySide6 import QtCore
from asyncslot import AsyncSlotSelectorEventLoop


async def test():
    for name in ('Alice', 'Bob'):
        print(f'Hi, {name}!')
        await asyncio.sleep(1)
    print('Bye-bye!')


def main():
    app = QtCore.QCoreApplication()
    loop = AsyncSlotSelectorEventLoop()
    try:
        loop.run_until_complete(test())
    finally:
        loop.close()


if __name__ == '__main__':
    main()

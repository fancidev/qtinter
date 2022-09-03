import asyncio
from PySide6 import QtCore
from asyncslot import AsyncSlotDefaultEventLoopPolicy


async def test():
    for name in ('Alice', 'Bob'):
        print(f'Hi, {name}!')
        await asyncio.sleep(1)
    print('Bye-bye!')


def main():
    app = QtCore.QCoreApplication()
    asyncio.set_event_loop_policy(AsyncSlotDefaultEventLoopPolicy())
    asyncio.run(test())


if __name__ == '__main__':
    main()

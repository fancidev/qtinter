import asyncio
import qtinter
from PySide6 import QtCore


async def test():
    for name in ('Alice', 'Bob'):
        print(f'Hi, {name}!')
        await asyncio.sleep(1)
    print('Bye-bye!')


def main():
    app = QtCore.QCoreApplication()
    asyncio.set_event_loop_policy(qtinter.QiDefaultEventLoopPolicy())
    asyncio.run(test())


if __name__ == '__main__':
    main()

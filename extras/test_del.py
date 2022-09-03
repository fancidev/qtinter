""" test_del.py - demo a strange bug with PySide6.QtCore """

import asyncio
import concurrent.futures
import selectors
from PySide6 import QtCore


async def noop():
    print('Hi')
    await asyncio.sleep(1)
    print('Bye')


class CustomSelector:
    def __init__(self):
        self._selector = selectors.DefaultSelector()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.shutdown(wait=True)
        executor = None

    def register(self, fileobj, events, data=None):
        return self._selector.register(fileobj, events, data)

    def unregister(self, fileobj):
        return self._selector.unregister(fileobj)

    def modify(self, fileobj, events, data=None):
        return self._selector.modify(fileobj, events, data)

    def select(self, timeout):
        return self._selector.select(timeout)

    def close(self):
        self._selector.close()

    def get_key(self, fileobj):
        return self._selector.get_key(fileobj)

    def get_map(self):
        return self._selector.get_map()


class NoopSelector(selectors.DefaultSelector):
    pass


class CustomEventLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        whatever = CustomSelector()
        selector = NoopSelector()
        super().__init__(selector)


def main():
    loop = CustomEventLoop()
    loop.run_until_complete(noop())


if __name__ == '__main__':
    main()

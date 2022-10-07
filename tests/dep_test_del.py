""" dep_test_del.py - demo a strange bug with PyQt6, PySide2 and PySide6

With certain code (unrelated to qtinter), these bindings raise an
exception in asyncio's event loop's __del__ method, complaining about
invalid file handle when attempting to unregister a self-read socket.
It appears that a reference cycle is created if a QtCore.QCoreApplication
instance is created.
"""

import asyncio
import concurrent.futures
import importlib
import selectors
import os

qt_binding_name = os.getenv("TEST_QT_BINDING", "")
if not qt_binding_name:
    raise RuntimeError("TEST_QT_BINDING must be specified")

QtCore = importlib.import_module(f"{qt_binding_name}.QtCore")


async def noop():
    pass


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


class CustomEventLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        whatever = CustomSelector()
        whatever = None
        selector = selectors.DefaultSelector()
        super().__init__(selector)


def main():
    app = QtCore.QCoreApplication([])
    loop = CustomEventLoop()
    loop.run_until_complete(noop())


if __name__ == '__main__':
    main()

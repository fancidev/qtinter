import asyncio
import qtinter
import unittest
from shim import QtCore


class TestSignal(unittest.TestCase):

    def setUp(self) -> None:
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self) -> None:
        self.app = None

    def test_timer(self):
        timer = QtCore.QTimer()
        timer.setInterval(100)
        timer.start()

        async def coro():
            await qtinter.asyncsignal(timer.timeout)
            return 123

        with qtinter.using_qt_from_asyncio():
            self.assertEqual(asyncio.run(coro()), 123)


if __name__ == "__main__":
    unittest.main()

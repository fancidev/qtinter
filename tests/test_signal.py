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

    def test_cancellation(self):
        # asyncsignal should be able to be cancelled
        timer = QtCore.QTimer()
        timer.setInterval(0)

        async def coro():
            await qtinter.asyncsignal(timer.timeout)

        async def main():
            task = asyncio.create_task(coro())
            await asyncio.sleep(0)
            task.cancel()
            timer.start()
            await task

        with qtinter.using_qt_from_asyncio():
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(main())

    @unittest.skip("not supported yet")
    def test_sender_gone(self):
        # If the sender is garbage collected, asyncsignal should
        # raise CancelledError.
        timer = QtCore.QTimer()
        timer.setInterval(100)
        timer.start()

        def delete_timer():
            nonlocal timer
            timer = None

        async def coro():
            asyncio.get_running_loop().call_soon(delete_timer)
            await qtinter.asyncsignal(timer.timeout)
            return 123

        with qtinter.using_qt_from_asyncio():
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(coro())

    def test_sender_gone_timeout(self):
        # Timeout on sender gone should work.
        timer = QtCore.QTimer()
        timer.setInterval(100)
        timer.start()

        def delete_timer():
            nonlocal timer
            timer = None

        async def coro():
            asyncio.get_running_loop().call_soon(delete_timer)
            await qtinter.asyncsignal(timer.timeout)
            return 123

        async def main():
            await asyncio.wait_for(coro(), 1.0)

        with qtinter.using_qt_from_asyncio():
            with self.assertRaises(asyncio.TimeoutError):
                asyncio.run(main())

    # @unittest.skip("not supported yet")
    def test_destroyed(self):
        # Should be able to catch destroyed signal
        timer = QtCore.QTimer()
        timer.setInterval(100)
        timer.start()

        def delete_timer():
            nonlocal timer
            timer = None

        async def coro():
            asyncio.get_running_loop().call_soon(delete_timer)
            await qtinter.asyncsignal(timer.destroyed)
            return 123

        with qtinter.using_qt_from_asyncio():
            self.assertEqual(asyncio.run(coro()), 123)


if __name__ == "__main__":
    unittest.main()

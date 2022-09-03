from shim import QtCore
import asyncio
import time
import unittest
import asyncslot


class TestSleep(unittest.TestCase):

    def setUp(self) -> None:
        if QtCore.QCoreApplication.instance() is None:
            self.app = QtCore.QCoreApplication([])
        self.loop = asyncslot.AsyncSlotDefaultEventLoop()

    def tearDown(self) -> None:
        self.loop.close()

    def test_sleep(self):
        total_time = 0.0

        async def sleep_for(times, duration):
            for _ in range(times):
                await asyncio.sleep(duration)

        async def entry():
            nonlocal total_time
            t1 = time.time()
            await asyncio.gather(sleep_for(4, 1.0), sleep_for(2, 2.0))
            t2 = time.time()
            total_time = t2 - t1

        self.loop.run_until_complete(entry())
        self.assertGreater(total_time, 3.5)
        self.assertLess(total_time, 4.5)


if __name__ == '__main__':
    unittest.main()

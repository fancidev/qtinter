from shim import QtCore
import asyncio
import qtinter
import time
import unittest


class TestSleep(unittest.TestCase):

    def setUp(self) -> None:
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])
        self.loop = qtinter.QiDefaultEventLoop()

    def tearDown(self) -> None:
        self.loop.close()
        self.app = None

    def test_sleep(self):
        total_duration = 2.0

        async def sleep_for(times):
            for _ in range(times):
                await asyncio.sleep(total_duration / times)

        async def entry():
            t1 = time.time()
            tasks = []
            for _ in range(100):
                tasks.append(sleep_for(8))
                tasks.append(sleep_for(4))
                tasks.append(sleep_for(2))
                tasks.append(sleep_for(1))
            await asyncio.gather(*tasks)
            t2 = time.time()
            return t2 - t1

        total_time = self.loop.run_until_complete(entry())
        self.assertGreater(total_time, total_duration - 0.1)
        self.assertLess(total_time, total_duration + 1.0)


if __name__ == '__main__':
    unittest.main()

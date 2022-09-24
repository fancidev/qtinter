import asyncslot
import signal
import sys
import threading
import time
import unittest
from shim import QtCore


def _noop():
    pass


class TestCtrlC(unittest.TestCase):
    # A collection of test cases for the behavior of Ctrl+C for a loop
    # operating in host mode.  The expected behavior is to propagate
    # KeyboardInterrupt to the caller of run_forever.
    #
    # Adapted from test.test_asyncio.test_windows_events.ProactorLoopCtrlC
    # but also tests unix event loops.

    def setUp(self) -> None:
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self) -> None:
        self.app = None

    def _test_ctrl_c(self, loop):
        def SIGINT_after_delay():
            time.sleep(0.1)
            signal.raise_signal(signal.SIGINT)

        thread = threading.Thread(target=SIGINT_after_delay)
        try:
            with self.assertRaises(KeyboardInterrupt):
                loop.call_soon(thread.start)
                loop.run_forever()
        finally:
            loop.close()


@unittest.skipIf(sys.platform == 'win32', 'unix only')
class TestUnixCtrlC(TestCtrlC):
    """Test Ctrl+C under unix."""

    def test_unix_loop(self):
        self._test_ctrl_c(asyncslot.AsyncSlotDefaultEventLoop())

    def test_unix_loop_with_SIGCHLD_1(self):
        loop = asyncslot.AsyncSlotDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _noop)
        self._test_ctrl_c(loop)

    def test_unix_loop_with_SIGCHLD_2(self):
        loop = asyncslot.AsyncSlotDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _noop)
        loop.remove_signal_handler(signal.SIGCHLD)
        self._test_ctrl_c(loop)

    def test_unix_loop_with_SIGINT_1(self):
        loop = asyncslot.AsyncSlotDefaultEventLoop()
        loop.add_signal_handler(signal.SIGINT, signal.default_int_handler)
        self._test_ctrl_c(loop)

    def test_unix_loop_with_SIGINT_2(self):
        loop = asyncslot.AsyncSlotDefaultEventLoop()
        loop.add_signal_handler(signal.SIGINT, signal.default_int_handler)
        loop.remove_signal_handler(signal.SIGINT)
        self._test_ctrl_c(loop)


@unittest.skipUnless(sys.platform == 'win32', 'windows only')
class TestWindowsCtrlC(TestCtrlC):
    """Test Ctrl+C under windows."""

    def test_windows_proactor_loop(self):
        self._test_ctrl_c(asyncslot.AsyncSlotProactorEventLoop())

    def test_windows_selector_loop(self):
        self._test_ctrl_c(asyncslot.AsyncSlotSelectorEventLoop())


if __name__ == '__main__':
    unittest.main()

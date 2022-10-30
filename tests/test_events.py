import asyncio
import os
import qtinter
import signal
import sys
import threading
import time
import unittest
import warnings
from test.support.script_helper import run_python_until_end
from shim import QtCore


warnings.filterwarnings('default')
folder = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _raise_ki():
    return signal.default_int_handler(signal.SIGINT, None)


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
            if sys.version_info < (3, 8):
                import os
                os.kill(os.getpid(), signal.SIGINT)
            else:
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
        self._test_ctrl_c(qtinter.QiDefaultEventLoop())

    def test_unix_loop_with_SIGCHLD_1(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _raise_ki)
        self._test_ctrl_c(loop)

    def test_unix_loop_with_SIGCHLD_2(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _raise_ki)
        loop.remove_signal_handler(signal.SIGCHLD)
        self._test_ctrl_c(loop)

    def test_unix_loop_with_SIGINT_1(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGINT, _raise_ki)
        self._test_ctrl_c(loop)

    def test_unix_loop_with_SIGINT_2(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGINT, _raise_ki)
        loop.remove_signal_handler(signal.SIGINT)
        self._test_ctrl_c(loop)


# The Windows Ctrl+C test is not run for Python 3.7, for two reasons:
# - First, the proactor event loop in Python 3.7 does not support being
#   interrupted by Ctrl+C; see https://github.com/python/cpython/issues/67246
# - Second, Python 3.7 does not have the raise_signal function, and
#   os.kill(SIGINT) does not work under Windows; see
#   https://stackoverflow.com/questions/35772001/how-to-handle-a-signal-sigint-on-a-windows-os-machine
@unittest.skipUnless(sys.platform == 'win32', 'windows only')
@unittest.skipUnless(sys.version_info >= (3, 8), 'requires python >= 3.8')
class TestWindowsCtrlC(TestCtrlC):
    """Test Ctrl+C under windows."""

    def test_windows_proactor_loop(self):
        self._test_ctrl_c(qtinter.QiProactorEventLoop())

    def test_windows_selector_loop(self):
        self._test_ctrl_c(qtinter.QiSelectorEventLoop())


def exec_qt_loop(loop):
    if hasattr(loop, 'exec'):
        loop.exec()
    else:
        loop.exec_()


class TestModal(unittest.TestCase):
    """Tests related to modal support"""

    def setUp(self) -> None:
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self) -> None:
        self.app = None

    def test_non_modal(self):
        # Running nested Qt event loop without modal wrapper should block
        # the asyncio event loop.
        loop = qtinter.QiDefaultEventLoop()
        t1 = loop.time()
        t2 = 0

        def cb1():
            nested = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(1000, nested.quit)
            exec_qt_loop(nested)

        def cb2():
            nonlocal t2
            t2 = loop.time()
            loop.stop()

        loop.call_soon(cb1)
        loop.call_soon(cb2)
        loop.run_forever()
        loop.close()
        t3 = loop.time()

        self.assertTrue(0.8 <= t2 - t1 <= 1.5, t2 - t1)
        self.assertTrue(0 <= t3 - t2 <= 0.1, t3 - t2)

    def test_exec_modal_nested(self):
        # exec_modal() of QEventLoop.exec should keep the asyncio event loop
        # running.
        loop = qtinter.QiDefaultEventLoop()
        t1 = loop.time()
        t2 = 0
        var = 0

        def cb1():
            nested = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(1000, nested.quit)
            loop.exec_modal(lambda: exec_qt_loop(nested))

        def cb2():
            nonlocal t2
            t2 = loop.time()
            # QtCore.QCoreApplication.exit()
            loop.stop()  # will only stop after nested loop exits
            loop.call_soon(cb3)  # should not call

        def cb3():
            nonlocal var
            var = 1

        loop.call_soon(cb1)
        loop.call_soon(cb2)
        loop.run_forever()
        loop.close()
        t3 = loop.time()

        self.assertTrue(0 <= t2 - t1 <= 0.5, t2 - t1)
        self.assertTrue(0.8 <= t3 - t1 <= 1.5, t3 - t1)
        self.assertEqual(var, 0)

    def test_modal_wrapper(self):
        # qtinter.modal() wrapper should keep event loop running.
        async def counter(nested):
            for i in range(5):
                await asyncio.sleep(0.1)
            nested.quit()
            return 123

        async def coro():
            nested = QtCore.QEventLoop()
            task = asyncio.create_task(counter(nested))
            await qtinter.modal(exec_qt_loop)(nested)
            return await task

        loop = qtinter.QiDefaultEventLoop()
        t1 = loop.time()
        result = loop.run_until_complete(coro())
        t2 = loop.time()
        loop.close()
        t3 = loop.time()

        self.assertEqual(result, 123)
        self.assertTrue(0.4 < t2 - t1 < 1.5, t2 - t1)
        self.assertTrue(0 <= t3 - t2 < 1.0, t3 - t2)

    def test_modal_alien_loop(self):
        # Calling qtinter.modal on a plain asyncio loop raises RuntimeError.
        def f():
            pass

        async def coro():
            await qtinter.modal(f)()

        with self.assertRaisesRegex(RuntimeError, 'requires QiBaseEventLoop'):
            asyncio.run(coro())

    def test_modal_exception(self):
        # qtinter.modal should propagate the exception raised.
        class MyError(RuntimeError):
            pass

        def f():
            raise MyError

        async def coro():
            await qtinter.modal(f)()

        with qtinter.using_qt_from_asyncio():
            with self.assertRaises(MyError):
                asyncio.run(coro())

    # def test_pause_resume(self):
    #     # If a callback raised SystemExit and is handled, rerunning the
    #     # loop should pick up from where it left off without polling or
    #     # executing additional callbacks.
    #     import selectors
    #
    #     class SelectOnce(selectors.DefaultSelector):
    #         def __init__(self):
    #             super().__init__()
    #             self.__called = False
    #
    #         def select(self, *args):
    #             assert not self.__called, 'should call select() only once'
    #             self.__called = True
    #             return super().select(*args)
    #
    #     var = 0
    #
    #     def inc():
    #         nonlocal var, loop
    #         var += 1
    #         loop.call_soon(inc)  # this callback should not be called
    #
    #     loop = qtinter.QiSelectorEventLoop(SelectOnce())
    #     loop.call_soon(inc)
    #     loop.call_soon(sys.exit)
    #     loop.call_soon(loop.stop)
    #
    #     with self.assertRaises(SystemExit):
    #         loop.run_forever()
    #     loop.run_forever()
    #     loop.close()
    #     self.assertEqual(var, 1)
    #
    # def test_call_next_outside_callback(self):
    #     # Calling call_next() outside of a callback should raise RuntimeError
    #     def fn(): pass
    #
    #     loop = qtinter.QiDefaultEventLoop()
    #     with self.assertRaises(RuntimeError):
    #         loop.call_next(fn)
    #     loop.close()
    #
    # def test_call_next_from_callback(self):
    #     # call_next should be invoked immediately
    #     var = 3
    #
    #     def f():
    #         nonlocal var
    #         loop.call_next(g)
    #         var += 4
    #
    #     def g():
    #         nonlocal var
    #         var *= 5
    #
    #     loop = qtinter.QiDefaultEventLoop()
    #     loop.call_soon(f)
    #     loop.call_soon(sys.exit)
    #     with self.assertRaises(SystemExit):
    #         loop.run_forever()
    #     loop.close()
    #     self.assertEqual(var, 35)


class TestRunner(unittest.TestCase):
    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def test_new_event_loop(self):
        async def stop():
            result.set_result(123)

        async def coro():
            QtCore.QTimer.singleShot(0, qtinter.asyncslot(stop))
            await result

        loop = qtinter.new_event_loop()
        result = loop.create_future()
        loop.run_until_complete(coro())
        loop.close()
        self.assertEqual(result.result(), 123)

    @unittest.skipIf(sys.version_info < (3, 11), "requires Python >= 3.11")
    def test_runner(self):
        async def coro():
            future = asyncio.Future()
            QtCore.QTimer.singleShot(
                0, lambda: future.set_result(123))
            return await future

        with asyncio.Runner(loop_factory=qtinter.new_event_loop) as runner:
            self.assertEqual(runner.run(coro()), 123)

    def test_no_application(self):
        # Running qtinter loop without QCoreApplication raises RuntimeError.
        result, cmd = run_python_until_end(
            os.path.join("tests", "runner1.py"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(result.rc, 1)
        stderr = str(result.err, encoding="utf-8")
        self.assertIn("RuntimeError: An instance of QCoreApplication", stderr)

    def test_application_exited_before_loop(self):
        # Running qtinter after QCoreApplication.exit() raises RuntimeError
        result, cmd = run_python_until_end(
            os.path.join("tests", "runner2.py"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(result.rc, 1)
        # result.fail(cmd)
        stderr = str(result.err, encoding="utf-8")
        self.assertIn("RuntimeError: Qt event loop exited with code '-1'",
                      stderr)

    def test_application_exited_during_loop(self):
        # If QCoreApplication.quit() is called from a coroutine or callback
        # within using_qt_from_asyncio, a RuntimeError will be raised when
        # cleaning up the loop because the clean-up procedure runs the loop
        # but it can no longer be run.
        result, cmd = run_python_until_end(
            os.path.join("tests", "runner3.py"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(result.rc, 1)
        # result.fail(cmd)
        stderr = str(result.err, encoding="utf-8")
        self.assertIn("RuntimeError: Qt event loop exited with code '-1'",
                      stderr)

    def test_incompatible_using_asyncio_from_qt(self):
        with qtinter.using_asyncio_from_qt():
            loop = asyncio.get_running_loop()
            self.assertIsInstance(loop, qtinter.QiBaseEventLoop)
            with self.assertRaisesRegex(
                    RuntimeError,
                    "cannot be called for a loop operating in GUEST mode"):
                loop.run_forever()


if __name__ == '__main__':
    unittest.main()

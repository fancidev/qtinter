import asyncio
import os
import qtinter
import signal
import sys
import threading
import time
import unittest
import warnings
from shim import QtCore, run_test_script, is_pyqt


warnings.filterwarnings('default')


def _raise_ki():
    return signal.default_int_handler(signal.SIGINT, None)


def _no_op_SIGINT_handler(sig, frame):
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

    def _test_ctrl_c_while_selecting(self, loop):
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

    def _test_ctrl_c_while_processing(self, loop):
        def SIGINT_after_delay():
            time.sleep(0.5)
            if sys.version_info < (3, 8):
                import os
                os.kill(os.getpid(), signal.SIGINT)
            else:
                signal.raise_signal(signal.SIGINT)

        async def coro():
            while True:
                pass

        thread = threading.Thread(target=SIGINT_after_delay)
        try:
            with self.assertRaises(KeyboardInterrupt):
                loop.call_soon(thread.start)
                loop.run_until_complete(coro())
        finally:
            loop.close()

    def _test_ctrl_c_suppressed_1(self, loop):
        # User should be able to suppress Ctrl+C by installing a no-op handler.
        async def coro():
            pass

        signal.signal(signal.SIGINT, _no_op_SIGINT_handler)
        try:
            self.assertEqual(loop.run_until_complete(coro()), None)
        finally:
            self.assertIs(signal.getsignal(signal.SIGINT),
                          _no_op_SIGINT_handler)
            signal.signal(signal.SIGINT, signal.default_int_handler)
            loop.close()

    def _test_ctrl_c_suppressed_2(self, loop):
        # User should be able to suppress Ctrl+C by installing a no-op handler.
        async def coro():
            signal.signal(signal.SIGINT, _no_op_SIGINT_handler)

        try:
            self.assertEqual(loop.run_until_complete(coro()), None)
        finally:
            self.assertIs(signal.getsignal(signal.SIGINT),
                          _no_op_SIGINT_handler)
            signal.signal(signal.SIGINT, signal.default_int_handler)
            loop.close()


@unittest.skipIf(sys.platform == 'win32', 'unix only')
class TestUnixCtrlC(TestCtrlC):
    """Test Ctrl+C under unix."""

    def test_unix_loop(self):
        self._test_ctrl_c_while_selecting(qtinter.QiDefaultEventLoop())
        self._test_ctrl_c_while_processing(qtinter.QiDefaultEventLoop())

    def test_unix_loop_with_SIGCHLD_1_selecting(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _raise_ki)
        self._test_ctrl_c_while_selecting(loop)

    def test_unix_loop_with_SIGCHLD_1_processing(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _raise_ki)
        self._test_ctrl_c_while_processing(loop)

    def test_unix_loop_with_SIGCHLD_2_selecting(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _raise_ki)
        loop.remove_signal_handler(signal.SIGCHLD)
        self._test_ctrl_c_while_selecting(loop)

    def test_unix_loop_with_SIGCHLD_2_processing(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGCHLD, _raise_ki)
        loop.remove_signal_handler(signal.SIGCHLD)
        self._test_ctrl_c_while_processing(loop)

    def test_unix_loop_with_SIGINT_1_selecting(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGINT, _raise_ki)
        self._test_ctrl_c_while_selecting(loop)

    # The following test will hang by construction, because add_signal_handler
    # schedules the handler as a callback in the event loop, which has no
    # chance to run if the event loop is busy processing.
    # def test_unix_loop_with_SIGINT_1_processing(self):
    #     loop = qtinter.QiDefaultEventLoop()
    #     loop.add_signal_handler(signal.SIGINT, _raise_ki)
    #     self._test_ctrl_c_while_processing(loop)

    def test_unix_loop_with_SIGINT_2_selecting(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGINT, _raise_ki)
        loop.remove_signal_handler(signal.SIGINT)
        self._test_ctrl_c_while_selecting(loop)

    def test_unix_loop_with_SIGINT_2_processing(self):
        loop = qtinter.QiDefaultEventLoop()
        loop.add_signal_handler(signal.SIGINT, _raise_ki)
        loop.remove_signal_handler(signal.SIGINT)
        self._test_ctrl_c_while_processing(loop)

    def test_unix_loop_ctrl_c_suppressed_1(self):
        loop = qtinter.QiDefaultEventLoop()
        self._test_ctrl_c_suppressed_1(loop)

    def test_unix_loop_ctrl_c_suppressed_2(self):
        loop = qtinter.QiDefaultEventLoop()
        self._test_ctrl_c_suppressed_2(loop)


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

    def test_windows_proactor_loop_selecting(self):
        self._test_ctrl_c_while_selecting(qtinter.QiProactorEventLoop())

    def test_windows_proactor_loop_processing(self):
        self._test_ctrl_c_while_processing(qtinter.QiProactorEventLoop())

    def test_windows_selector_loop_selecting(self):
        self._test_ctrl_c_while_selecting(qtinter.QiSelectorEventLoop())

    def test_windows_selector_loop_processing(self):
        self._test_ctrl_c_while_processing(qtinter.QiSelectorEventLoop())

    def test_windows_proactor_loop_ctrl_c_suppressed_1(self):
        loop = qtinter.QiProactorEventLoop()
        self._test_ctrl_c_suppressed_1(loop)

    def test_windows_proactor_loop_ctrl_c_suppressed_2(self):
        loop = qtinter.QiProactorEventLoop()
        self._test_ctrl_c_suppressed_2(loop)

    def test_windows_selector_loop_ctrl_c_suppressed_1(self):
        loop = qtinter.QiSelectorEventLoop()
        self._test_ctrl_c_suppressed_1(loop)

    def test_windows_selector_loop_ctrl_c_suppressed_2(self):
        loop = qtinter.QiSelectorEventLoop()
        self._test_ctrl_c_suppressed_2(loop)


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

    def test_exec_modal_outside_callback(self):
        # Calling exec_modal() outside a callback should raise RuntimeError
        def fn(): pass

        loop = qtinter.QiDefaultEventLoop()
        with self.assertRaisesRegex(
                RuntimeError, 'must be called from a coroutine or callback'):
            loop.exec_modal(fn)
        loop.close()

    def test_exec_modal_from_callback(self):
        # Calling exec_modal(fn) should execute fn immediately after the
        # current callback.
        var = 3

        def f():
            nonlocal var
            loop.exec_modal(g)
            var += 4

        def g():
            nonlocal var
            var *= 5

        loop = qtinter.QiDefaultEventLoop()
        loop.call_soon(f)
        loop.call_soon(sys.exit)
        with self.assertRaises(SystemExit):
            loop.run_forever()
        loop.close()
        self.assertEqual(var, 35)

    def test_exec_modal_twice(self):
        # Calling exec_modal() twice from the same callback is an error.
        var = 3

        def f():
            nonlocal var
            loop.exec_modal(g)
            with self.assertRaisesRegex(
                RuntimeError, 'already scheduled and pending'
            ):
                loop.exec_modal(g)
            var += 4

        def g():
            nonlocal var
            var *= 5

        loop = qtinter.QiDefaultEventLoop()
        loop.call_soon(f)
        loop.call_soon(sys.exit)
        with self.assertRaises(SystemExit):
            loop.run_forever()
        loop.close()
        self.assertEqual(var, 35)

    def test_exec_modal_recursive(self):
        # Calling exec_modal() from exec_modal is an error (because the
        # function is executed out of asyncio loop context).
        var = 3

        def f():
            nonlocal var
            loop.exec_modal(g)
            var += 4

        def g():
            nonlocal var
            with self.assertRaisesRegex(
                RuntimeError, 'must be called from a coroutine or callback'
            ):
                loop.exec_modal(h)
            var *= 5

        def h():
            pass

        loop = qtinter.QiDefaultEventLoop()
        loop.call_soon(f)
        loop.call_soon(sys.exit)
        with self.assertRaises(SystemExit):
            loop.run_forever()
        loop.close()
        self.assertEqual(var, 35)

    def test_exec_modal_in_native_mode(self):
        # exec_modal() is not supported in NATIVE mode.  So, for example, it
        # cannot be called in clean-up code of using_asyncio_from_qt.
        var = 0

        def f():
            nonlocal var
            var = 1  # should not execute

        async def coro():
            nonlocal var
            try:
                await asyncio.sleep(1000)
            except asyncio.CancelledError:  # clean-up
                with self.assertRaisesRegex(
                    RuntimeError, 'not supported in NATIVE mode'
                ):
                    await qtinter.modal(f)()
                var = 2  # should execute

        with qtinter.using_asyncio_from_qt():
            task = asyncio.create_task(coro())
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(100, loop.quit)
            exec_qt_loop(loop)
        self.assertEqual(var, 2)


class TestSelectorEventLoop(unittest.TestCase):
    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def test_reader_writer(self):
        reader_flag = b''

        import socket
        csock, ssock = socket.socketpair()

        def reader_callback():
            nonlocal reader_flag
            reader_flag = csock.recv(1)

        def writer_callback():
            self.assertEqual(len(loop._selector.get_map()), map_len + 1)
            csock.send(b'w')
            loop.remove_writer(csock)

        with qtinter.using_asyncio_from_qt(
                loop_factory=qtinter.QiSelectorEventLoop):

            loop = asyncio.get_running_loop()
            map_len = len(loop._selector.get_map())  # for branch coverage
            loop.add_reader(csock, reader_callback)
            loop.add_writer(csock, writer_callback)

            qt_loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(0, lambda: ssock.send(b'h'))
            QtCore.QTimer.singleShot(10, qt_loop.quit)
            exec_qt_loop(qt_loop)

        self.assertEqual(reader_flag, b'h')
        self.assertEqual(ssock.recv(10), b'w')
        csock.close()
        ssock.close()

    def test_close_when_running(self):
        async def coro():
            asyncio.get_running_loop().close()

        loop = qtinter.QiSelectorEventLoop()
        with self.assertRaisesRegex(
                RuntimeError, "Cannot close a running event loop"):
            loop.run_until_complete(coro())
        loop.close()


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
        rc, out, err = run_test_script(
            "runner1.py",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 1)
        self.assertIn("RuntimeError: An instance of QCoreApplication", err)

    def test_application_exited_before_loop(self):
        # Running qtinter after QCoreApplication.exit() raises RuntimeError
        rc, out, err = run_test_script(
            "runner2.py",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 1)
        self.assertIn("RuntimeError: Qt event loop exited with code '-1'", err)

    def test_application_exited_during_loop(self):
        # If QCoreApplication.quit() is called from a coroutine or callback
        # within using_qt_from_asyncio, a RuntimeError will be raised when
        # cleaning up the loop because the clean-up procedure runs the loop
        # but it can no longer be run.
        rc, out, err = run_test_script(
            "runner3.py",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 1)
        self.assertIn("RuntimeError: Qt event loop exited with code '-1'", err)

    def test_guest_mode_KeyboardInterrupt(self):
        # In guest mode, a KeyboardInterrupt exception raised by a callback
        # is propagated into the Qt event loop, which terminates the process
        # with a non-zero exit code.
        rc, out, err = run_test_script(
            "runner4.py",
            "KeyboardInterrupt",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        if is_pyqt:
            if sys.platform == 'win32':
                self.assertEqual(rc, 0xC0000409)
                self.assertEqual(out, "")
                self.assertEqual(err, "")
            else:
                self.assertEqual(rc, -6)  # SIGABRT
                self.assertEqual(out, "")
                self.assertIn("Fatal Python error: Aborted", err)
                self.assertIn("KeyboardInterrupt", err)
        else:
            self.assertEqual(rc, 0)
            self.assertEqual(out.strip(), "post exec")
            self.assertIn("KeyboardInterrupt", err)

    def test_guest_mode_SystemExit(self):
        # In guest mode, a SystemExit exception raised by a callback
        # is propagated into the Qt event loop, which then terminates
        # the process with exit code 0.
        rc, out, err = run_test_script(
            "runner4.py",
            "SystemExit",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")

    def test_guest_mode_Exception(self):
        # In guest mode, an Exception raised by a callback (ArithmeticError
        # in this case) is 'consumed' by the asyncio event loop's exception
        # handler, which merely logs the error to stderr.
        rc, out, err = run_test_script(
            "runner4.py",
            "ArithmeticError",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "post exec")
        self.assertIn("ArithmeticError", err)

    def test_owner_mode_SystemExit(self):
        # In owner mode, a SystemExit exception raised by a callback is
        # propagated to the caller.
        async def coro():
            raise SystemExit

        with qtinter.using_qt_from_asyncio():
            with self.assertRaises(SystemExit):
                asyncio.run(coro())

    def test_incompatible_loop_mode(self):
        with qtinter.using_asyncio_from_qt():
            loop = asyncio.get_running_loop()
            self.assertIsInstance(loop, qtinter.QiBaseEventLoop)
            with self.assertRaisesRegex(
                    RuntimeError,
                    "cannot be called for a loop operating in GUEST mode"):
                loop.run_forever()

    def test_change_mode_in_bad_state(self):
        # Cannot change the loop mode when running, stopping or closed.
        async def coro():
            loop.set_mode(qtinter.QiLoopMode.NATIVE)

        loop = qtinter.new_event_loop()
        with self.assertRaisesRegex(RuntimeError, "loop is already running"):
            loop.run_until_complete(coro())

        loop.stop()
        with self.assertRaisesRegex(RuntimeError, "when the loop is stopping"):
            loop.set_mode(qtinter.QiLoopMode.NATIVE)

        loop.close()
        with self.assertRaisesRegex(RuntimeError, "loop is closed"):
            loop.set_mode(qtinter.QiLoopMode.NATIVE)

    def test_auto_stop(self):
        # In OWNER mode, closing the underlying Qt event loop automatically
        # stops the running asyncio event loop, even if it is blocked in
        # select.
        def quit():
            # User code is more likely to call QtCore.QCoreApplication.quit(),
            # but that doesn't work well with unit testing.  Therefore we use
            # 'white-box' testing below.
            loop._QiBaseEventLoop__qt_event_loop.quit()

        QtCore.QTimer.singleShot(100, quit)
        loop = qtinter.new_event_loop()
        t0 = loop.time()
        loop.run_forever()
        t1 = loop.time()
        loop.close()
        self.assertTrue(t1 - t0 < 1, t1 - t0)

    def test_start_stop(self):
        # Starting and stopping loop immediately should work.
        loop = qtinter.new_event_loop()
        loop.set_mode(qtinter.QiLoopMode.GUEST)
        loop.start()
        loop.stop()
        loop.close()

    def test_double_close(self):
        # It should be possible to call close() more than once.
        loop = qtinter.new_event_loop()
        loop.close()
        loop.close()

    def test_run_after_close(self):
        # run_forever after close should fail.
        loop = qtinter.new_event_loop()
        loop.close()
        self.assertRaises(RuntimeError, loop.run_forever)


class TestAsyncioFromQt(unittest.TestCase):
    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def test_optional_arguments(self):
        loop = QtCore.QEventLoop()

        async def coro():
            await asyncio.sleep(0)
            loop.quit()

        QtCore.QTimer.singleShot(0, qtinter.asyncslot(coro))

        with qtinter.using_asyncio_from_qt(
                loop_factory=qtinter.QiSelectorEventLoop, debug=True):
            exec_qt_loop(loop)

    def test_stop_from_callback(self):
        # Stopping an asyncio event loop has effect after completing the
        # current iteration.
        loop = QtCore.QEventLoop()
        var = 0

        def step1():
            nonlocal var
            asyncio.get_running_loop().call_soon(step3)
            asyncio.get_running_loop().stop()
            var = 1

        def step2():
            nonlocal var
            QtCore.QTimer.singleShot(100, loop.quit)
            var = 2

        def step3():  # called by clean-up routine
            nonlocal var
            var = 3

        with qtinter.using_asyncio_from_qt():
            asyncio.get_running_loop().call_soon(step1)
            asyncio.get_running_loop().call_soon(step2)
            loop = QtCore.QEventLoop()
            exec_qt_loop(loop)
            self.assertEqual(var, 2)  # step3 is not run in main loop

        self.assertEqual(var, 3)  # step3 is run in clean-up routine

    def test_stop_from_interleaved_code_in_guest_mode(self):
        # Stopping a QiBaseEventLoop from interleaved code in GUEST mode
        # takes immediate effect.
        loop = QtCore.QEventLoop()
        msg = None

        def step():
            nonlocal msg
            asyncio.get_running_loop().stop()
            try:
                asyncio.get_running_loop()
            except RuntimeError as exc:
                msg = str(exc)
            finally:
                loop.quit()

        QtCore.QTimer.singleShot(0, step)
        with qtinter.using_asyncio_from_qt():
            exec_qt_loop(loop)

        self.assertIn("no running event loop", msg)

    def test_stop_from_interleaved_code_in_owner_mode(self):
        # Stopping a QiBaseEventLoop from interleaved code in OWNER mode
        # is as if with call_soon_threadsafe.
        loop = qtinter.new_event_loop()
        QtCore.QTimer.singleShot(100, loop.stop)
        t0 = loop.time()
        loop.run_forever()
        t1 = loop.time()
        loop.close()
        self.assertTrue(t1 - t0 < 1, t1 - t0)

    def test_stop_twice(self):
        # Stopping a stopped QiBaseEventLoop in GUEST mode is an error.
        loop = QtCore.QEventLoop()
        var = 0
        msg = None

        def step1():
            nonlocal var
            asyncio_loop = asyncio.get_running_loop()
            asyncio_loop.stop()
            asyncio_loop.call_soon(step2)
            QtCore.QTimer.singleShot(100, lambda: step3(asyncio_loop))
            var = 1

        def step2():  # called from clean-up routine
            nonlocal var
            var = 2

        def step3(asyncio_loop):
            nonlocal msg
            try:
                asyncio_loop.stop()
            except RuntimeError as exc:
                msg = str(exc)
            loop.quit()

        with qtinter.using_asyncio_from_qt():
            asyncio.get_running_loop().call_soon(step1)
            exec_qt_loop(loop)
            self.assertEqual(var, 1)

        self.assertEqual(var, 2)
        self.assertIn("stop can only be called when a loop operating in "
                      "GUEST mode is running", msg)

    def test_wrong_mode(self):
        # Cannot call QiBaseEventLoop.start() in NATIVE or OWNER mode.
        loop = qtinter.new_event_loop()
        with self.assertRaisesRegex(RuntimeError, "operating in GUEST mode"):
            loop.start()

        loop.set_mode(qtinter.QiLoopMode.NATIVE)
        with self.assertRaisesRegex(RuntimeError, "operating in GUEST mode"):
            loop.start()

        # Must close the loop, or a KeyError will be raised when importing
        # a non-imported module in the next test case.  The root cause is
        # described at https://github.com/python/cpython/issues/91351
        loop.close()


class TestThreading(unittest.TestCase):
    # Test that QiBaseEventLoop works in a thread.

    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def test_owner_mode(self):
        # Simple test of OWNER mode in Python thread.
        var = 0

        async def coro():
            nonlocal var
            await asyncio.sleep(0)
            var = 1

        def entry():
            with qtinter.using_qt_from_asyncio():
                asyncio.run(coro())

        thread = threading.Thread(target=entry)
        thread.start()
        thread.join()

        self.assertEqual(var, 1)


if __name__ == '__main__':
    unittest.main()

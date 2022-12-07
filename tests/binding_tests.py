"""Test PyQt5/PyQt6/PySide2/PySide6 behavior"""

import os
import sys
import unittest
from shim import QtCore, Signal, Slot, is_pyqt, run_test_script


qc = QtCore.Qt.ConnectionType.QueuedConnection


class SenderObject(QtCore.QObject):
    signal = Signal(bool)


called = []


def visit(s, tag=None):
    if tag is not None:
        msg = f'{s}({tag.secret})'
    else:
        msg = s
    # print(msg)
    called.append(msg)


def _test_slot(slot):
    called.clear()
    sender = SenderObject()
    sender.signal.connect(slot)
    sender.signal.emit(True)
    return called.copy()


# -----------------------------------------------------------------------------
# Tests on free function slots
# -----------------------------------------------------------------------------

def func():
    visit('func')


@Slot()
def slot_func():
    visit('slot_func')


class TestFreeFunction(unittest.TestCase):

    def test_func(self):
        result = _test_slot(func)
        self.assertEqual(result, ['func'])

    def test_slot_func(self):
        result = _test_slot(slot_func)
        self.assertEqual(result, ['slot_func'])


# -----------------------------------------------------------------------------
# Tests on method slots
# -----------------------------------------------------------------------------

class Receiver:
    secret = 'Cls'

    def __init__(self):
        super().__init__()
        self.secret = 'Self'

    def method(self):
        visit('method', self)

    @Slot()
    def slot_method(self):
        visit('slot_method', self)

    @classmethod
    def class_method(cls):
        visit('class_method', cls)

    try:
        @Slot()
        @classmethod
        def slot_class_method(cls):
            visit('slot_class_method', cls)
    except AttributeError:
        # This construct is not supported on PyQt below Python 3.10.
        pass

    @classmethod
    @Slot()
    def class_slot_method(cls):
        visit('class_slot_method', cls)

    @staticmethod
    def static_method():
        visit('static_method')

    try:
        @Slot()
        @staticmethod
        def slot_static_method():
            visit('slot_static_method')
    except AttributeError:
        # This construct is not supported on PyQt below Python 3.10.
        pass

    @staticmethod
    @Slot()
    def static_slot_method():
        visit('static_slot_method')


class ReceiverObject(Receiver, QtCore.QObject):
    pass


class TestReceiverObject(unittest.TestCase):

    def setUp(self):
        self.receiver = ReceiverObject()

    def tearDown(self):
        self.receiver = None

    def test_method(self):
        result = _test_slot(self.receiver.method)
        self.assertEqual(result, ['method(Self)'])

    def test_slot_method(self):
        result = _test_slot(self.receiver.slot_method)
        self.assertEqual(result, ['slot_method(Self)'])

    def test_class_method(self):
        result = _test_slot(self.receiver.class_method)
        self.assertEqual(result, ['class_method(Cls)'])

    def test_slot_class_method(self):
        if is_pyqt and sys.version_info < (3, 10):
            # PyQt does not support such construct.
            self.assertFalse(hasattr(self.receiver, "slot_class_method"))
        else:
            result = _test_slot(self.receiver.slot_class_method)
            self.assertEqual(result, ['slot_class_method(Cls)'])

    def test_class_slot_method(self):
        if is_pyqt:
            # Not supported by PyQt
            with self.assertRaises(TypeError):
                _test_slot(self.receiver.class_slot_method)
        else:
            result = _test_slot(self.receiver.class_slot_method)
            self.assertEqual(result, ['class_slot_method(Cls)'])

    def test_static_method(self):
        result = _test_slot(self.receiver.static_method)
        self.assertEqual(result, ['static_method'])

    def test_slot_static_method(self):
        if is_pyqt and sys.version_info < (3, 10):
            # PyQt does not support such construct.
            self.assertFalse(hasattr(self.receiver, "slot_static_method"))
        else:
            result = _test_slot(self.receiver.slot_static_method)
            self.assertEqual(result, ['slot_static_method'])

    def test_static_slot_method(self):
        result = _test_slot(self.receiver.static_slot_method)
        self.assertEqual(result, ['static_slot_method'])


class TestReceiver(TestReceiverObject):
    def setUp(self):
        super().setUp()
        self.receiver = Receiver()

    def test_slot_method(self):
        if is_pyqt:
            # Not supported by PyQt
            with self.assertRaises(TypeError):
                super().test_slot_method()
        else:
            super().test_slot_method()


# -----------------------------------------------------------------------------
# Tests on receiver object without __weakref__ slot
# -----------------------------------------------------------------------------

class StrongReceiver:
    __slots__ = ()

    def method(self):
        called.append('special')


class StrongReceiverObject(StrongReceiver, QtCore.QObject):
    __slots__ = ()


class TestStrongReceiverObject(unittest.TestCase):
    def setUp(self):
        self.receiver = StrongReceiverObject()

    def tearDown(self):
        self.receiver = None

    def test_method(self):
        result = _test_slot(self.receiver.method)
        self.assertEqual(result, ['special'])


class TestStrongReceiver(TestStrongReceiverObject):
    def setUp(self):
        super().setUp()
        self.receiver = StrongReceiver()

    def test_method(self):
        with self.assertRaises(SystemError if is_pyqt else TypeError):
            _test_slot(self.receiver.method)


# -----------------------------------------------------------------------------
# Tests on multiple signature for same signal name
# -----------------------------------------------------------------------------

class Control(QtCore.QObject):
    valueChanged = Signal((int,), (str,))


class Widget(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.control1 = Control(self)
        self.control1.setObjectName("control1")
        self.control2 = Control(self)
        self.control2.setObjectName("control2")
        self.control3 = Control(self)
        self.control3.setObjectName("control3")
        self.control4 = Control(self)
        self.control4.setObjectName("control4")
        self.metaObject().connectSlotsByName(self)
        self.values = []

    def on_control1_valueChanged(self, newValue):
        self.values.append("control1")
        self.values.append(newValue)

    @Slot(int)
    def on_control2_valueChanged(self, newValue):
        self.values.append("control2")
        self.values.append(newValue)

    @Slot(str)
    def on_control3_valueChanged(self, newValue):
        self.values.append("control3")
        self.values.append(newValue)

    @Slot(int)
    @Slot(str)
    def on_control4_valueChanged(self, newValue):
        self.values.append("control4")
        self.values.append(newValue)


class TestSlotSelection(unittest.TestCase):
    def test_slot_selection(self):
        values1 = []
        values2 = []
        values3 = []
        values4 = []

        def callback():
            w = Widget()

            w.values.clear()
            w.control1.valueChanged[int].emit(12)
            w.control1.valueChanged[str].emit('ha')
            values1[:] = w.values

            w.values.clear()
            w.control2.valueChanged[int].emit(12)
            w.control2.valueChanged[str].emit('ha')
            values2[:] = w.values

            w.values.clear()
            w.control3.valueChanged[int].emit(12)
            w.control3.valueChanged[str].emit('ha')
            values3[:] = w.values

            w.values.clear()
            w.control4.valueChanged[int].emit(12)
            w.control4.valueChanged[str].emit('ha')
            values4[:] = w.values

        callback()

        if is_pyqt:
            self.assertEqual(values1, ["control1", 12, "control1", "ha"])
        else:
            self.assertEqual(values1, [])
        self.assertEqual(values2, ["control2", 12])
        self.assertEqual(values3, ["control3", "ha"])
        self.assertEqual(values4, ["control4", 12, "control4", "ha"])


class TestErrorHandling(unittest.TestCase):
    # PyQt aborts on unhandled exception.  PySide just logs to stderr.

    def test_raise_RuntimeError_from_slot(self):
        rc, out, err = run_test_script(
            "binding_raise.py", os.getenv("TEST_QT_MODULE"), "RuntimeError")
        if is_pyqt:
            if sys.platform == 'win32':
                self.assertEqual(rc, 0xC0000409)
                self.assertEqual(out, "")
                self.assertEqual(err, "")
            else:
                self.assertEqual(rc, -6)  # SIGABRT
                self.assertEqual(out, "")
                self.assertIn("Fatal Python error: Aborted", err)
        else:
            self.assertEqual(rc, 0)
            self.assertEqual(out.strip(), "post exec")
            self.assertIn("RuntimeError", err)

    def test_raise_SystemExit_from_slot(self):
        # SystemExit is handled.
        rc, out, err = run_test_script(
            "binding_raise.py", os.getenv("TEST_QT_MODULE"), "SystemExit")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")

    def test_raise_KeyboardInterrupt_from_slot(self):
        # SystemExit is handled.
        rc, out, err = run_test_script(
            "binding_raise.py",
            os.getenv("TEST_QT_MODULE"),
            "KeyboardInterrupt")
        if is_pyqt:
            if sys.platform == 'win32':
                self.assertEqual(rc, 0xC0000409)
                self.assertEqual(out, "")
                self.assertEqual(err, "")
            else:
                self.assertEqual(rc, -6)  # SIGABRT
                self.assertEqual(out, "")
                self.assertIn("Fatal Python error: Aborted", err)
        else:
            self.assertEqual(rc, 0)
            self.assertEqual(out.strip(), "post exec")
            self.assertIn("KeyboardInterrupt", err)


class Derived(Control):
    pass


class TestBoundSignal(unittest.TestCase):
    # Tests related to a bound signal.
    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def test_equality(self):
        # Two bound signal objects bound to the same sender and same signal
        # should compare equal.
        sender = Control()
        s = sender.valueChanged
        self.assertEqual(s, s)
        self.assertEqual(sender.valueChanged, sender.valueChanged)
        self.assertEqual(sender.valueChanged, sender.valueChanged[int])
        self.assertEqual(sender.valueChanged[int], sender.valueChanged[int])
        self.assertEqual(sender.valueChanged[str], sender.valueChanged[str])
        self.assertNotEqual(sender.valueChanged[int], sender.valueChanged[str])

        # When the signal is bound to an object of a derived class, some
        # versions of PySide2 has a bug that breaks equality.
        # See https://bugreports.qt.io/projects/PYSIDE/issues/PYSIDE-2140
        if QtCore.__name__.startswith('PySide2'):
            from PySide2 import __version__ as ver
            expect_broken = tuple(map(int, ver.split("."))) >= (5, 15, 2)
        else:
            expect_broken = False

        sender = Derived()
        s = sender.valueChanged
        self.assertEqual(s, s)
        if expect_broken:
            self.assertNotEqual(sender.valueChanged, sender.valueChanged)
            self.assertNotEqual(sender.valueChanged, sender.valueChanged[int])
            self.assertNotEqual(sender.valueChanged[int], sender.valueChanged[int])
            self.assertNotEqual(sender.valueChanged[str], sender.valueChanged[str])
        else:
            self.assertEqual(sender.valueChanged, sender.valueChanged)
            self.assertEqual(sender.valueChanged, sender.valueChanged[int])
            self.assertEqual(sender.valueChanged[int], sender.valueChanged[int])
            self.assertEqual(sender.valueChanged[str], sender.valueChanged[str])
        self.assertNotEqual(sender.valueChanged[int], sender.valueChanged[str])

    def test_identity(self):
        # Test the identity between two bound signal objects bound to the same
        # sender and same signal.  This is for information only; we should not
        # rely on any assumption of identity other than self identity.
        sender = Control()
        s = sender.valueChanged
        self.assertIs(s, s)
        if is_pyqt:
            self.assertIsNot(sender.valueChanged, sender.valueChanged)
            self.assertIsNot(sender.valueChanged, sender.valueChanged[int])
            self.assertIsNot(sender.valueChanged[int], sender.valueChanged[int])
            self.assertIsNot(sender.valueChanged[str], sender.valueChanged[str])
        else:
            self.assertIs(sender.valueChanged, sender.valueChanged)
            self.assertIs(sender.valueChanged, sender.valueChanged[int])
            self.assertIs(sender.valueChanged[int], sender.valueChanged[int])
            self.assertIs(sender.valueChanged[str], sender.valueChanged[str])
        self.assertIsNot(sender.valueChanged[int], sender.valueChanged[str])

        if QtCore.__name__.startswith('PySide2'):
            from PySide2 import __version__ as ver
            expect_broken = tuple(map(int, ver.split("."))) >= (5, 15, 2)
        else:
            expect_broken = False

        sender = Derived()
        s = sender.valueChanged
        self.assertIs(s, s)
        if is_pyqt or expect_broken:
            self.assertIsNot(sender.valueChanged, sender.valueChanged)
            self.assertIsNot(sender.valueChanged, sender.valueChanged[int])
            self.assertIsNot(sender.valueChanged[int], sender.valueChanged[int])
            self.assertIsNot(sender.valueChanged[str], sender.valueChanged[str])
        else:
            self.assertIs(sender.valueChanged, sender.valueChanged)
            self.assertIs(sender.valueChanged, sender.valueChanged[int])
            self.assertIs(sender.valueChanged[int], sender.valueChanged[int])
            self.assertIs(sender.valueChanged[str], sender.valueChanged[str])
        self.assertIsNot(sender.valueChanged[int], sender.valueChanged[str])

    def test_lifetime(self):
        # Test the lifetime of bound signal.
        # - If a queued signal is emitted but the sender is then deleted:
        #   On PySide: the queued callback IS NOT invoked
        #   On PyQt: the queued callback IS invoked.
        sender = SenderObject()
        var1 = 3
        var2 = 2

        def handler1(v):
            nonlocal var1
            var1 += {False: 15, True: 23}[v]

        def handler2(v):
            nonlocal var2
            var2 *= {False: -7, True: 2}[not v]

        bound_signal = sender.signal
        bound_signal.connect(handler1)
        bound_signal.connect(handler2, qc)
        bound_signal.emit(True)
        sender = None

        qt_loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(100, qt_loop.quit)
        if hasattr(qt_loop, "exec"):
            qt_loop.exec()
        else:
            qt_loop.exec_()

        self.assertEqual(var1, 26)
        if is_pyqt:
            self.assertEqual(var2, -14)
        else:
            self.assertEqual(var2, 2)

        # The following line would crash the process with SIGSEGV
        # under both PySide and PyQt.
        # bound_signal.emit(True)


class TestThread(unittest.TestCase):
    def test_loop_in_python_thread(self):
        # It should be possible to use Qt objects from a Python thread.
        # We run this test in a child process because the process sometimes
        # crashes with SIGSEGV after the test finishes (successfully) and
        # before the process is about to exit.  Likely a bug with PySide.
        rc, out, err = run_test_script(
            "binding_thread.py", os.getenv("TEST_QT_MODULE"), "MagicToken")
        if out.strip() != "MagicToken":
            print("binding_thread.py error:", file=sys.stderr)
            print(err, file=sys.stderr)
        self.assertEqual(out.strip(), "MagicToken")
        if rc != 0:
            print(f"binding_thread.py exited with code {rc}", file=sys.stderr)


if __name__ == '__main__':
    unittest.main()

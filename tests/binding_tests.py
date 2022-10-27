"""Test PyQt5/PyQt6/PySide2/PySide6 behavior"""

import importlib
import os
import unittest


binding_name = os.getenv("QTINTERBINDING", "")
is_pyqt = binding_name.startswith("PyQt")

QtCore = importlib.import_module(f"{binding_name}.QtCore")
if is_pyqt:
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
else:
    Signal = QtCore.Signal
    Slot = QtCore.Slot
qc = QtCore.Qt.ConnectionType.QueuedConnection


called = []


def visit(s, tag=None):
    if tag is not None:
        msg = f'{s}({tag.secret})'
    else:
        msg = s
    # print(msg)
    called.append(msg)


class MySignalObject(QtCore.QObject):
    ready = Signal(bool)


class MySlotNonObject:
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
        if is_pyqt:
            pass
        else:
            raise

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
        if is_pyqt:
            pass
        else:
            raise

    @staticmethod
    @Slot()
    def static_slot_method():
        visit('static_slot_method')


class MySlotObject(MySlotNonObject, QtCore.QObject):
    pass


def func():
    visit('func')


@Slot()
def slot_func():
    visit('slot_func')


def _test_slot(slot):
    called.clear()
    sender = MySignalObject()
    sender.ready.connect(slot)
    sender.ready.emit(True)
    return called.copy()


class TestSlotOnFreeFunction(unittest.TestCase):

    def test_func(self):
        result = _test_slot(func)
        self.assertEqual(result, ['func'])

    def test_slot_func(self):
        result = _test_slot(slot_func)
        self.assertEqual(result, ['slot_func'])


class TestSlotOnQObject(unittest.TestCase):

    def setUp(self):
        self.receiver = MySlotObject()

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
        if is_pyqt:
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
        if is_pyqt:
            # PyQt does not support such construct.
            self.assertFalse(hasattr(self.receiver, "slot_static_method"))
        else:
            result = _test_slot(self.receiver.slot_static_method)
            self.assertEqual(result, ['slot_static_method'])

    def test_static_slot_method(self):
        result = _test_slot(self.receiver.static_slot_method)
        self.assertEqual(result, ['static_slot_method'])


class TestSlotOnNonQObject(TestSlotOnQObject):
    def setUp(self):
        super().setUp()
        self.receiver = MySlotNonObject()

    def test_slot_method(self):
        if is_pyqt:
            # Not supported by PyQt
            with self.assertRaises(TypeError):
                super().test_slot_method()
        else:
            super().test_slot_method()


# class Sender(QtCore.QObject):
#     signal = Signal(int)
#
#
# class Receiver:
#     def __init__(self, output):
#         self.output = output
#
#     async def original_slot(self, v):
#         self.output[0] += v
#
#
# class StrongReceiver:
#     __slots__ = 'output',
#
#     def __init__(self, output):
#         self.output = output
#
#     def method(self, v):
#         self.output[0] -= v
#
#
# class Control(QtCore.QObject):
#     valueChanged = Signal((int,), (str,))
#
#
# class Widget(QtCore.QObject):
#     def __init__(self):
#         super().__init__()
#         self.control1 = Control(self)
#         self.control1.setObjectName("control1")
#         self.control2 = Control(self)
#         self.control2.setObjectName("control2")
#         self.control3 = Control(self)
#         self.control3.setObjectName("control3")
#         self.control4 = Control(self)
#         self.control4.setObjectName("control4")
#         self.metaObject().connectSlotsByName(self)
#         self.values = []
#
#     def on_control1_valueChanged(self, newValue):
#         self.values.append("control1")
#         self.values.append(newValue)
#
#     @Slot(int)
#     def on_control2_valueChanged(self, newValue):
#         self.values.append("control2")
#         self.values.append(newValue)
#
#     @asyncslot
#     async def on_control3_valueChanged(self, newValue):
#         self.values.append("control3")
#         self.values.append(newValue)
#
#     @asyncslot
#     @Slot(str)
#     async def on_control4_valueChanged(self, newValue):
#         self.values.append("control4")
#         self.values.append(newValue)
#
#
# class TestSlotSelection(unittest.TestCase):
#     def setUp(self) -> None:
#         if QtCore.QCoreApplication.instance() is not None:
#             self.app = QtCore.QCoreApplication.instance()
#         else:
#             self.app = QtCore.QCoreApplication([])
#
#     def tearDown(self) -> None:
#         self.app = None
#
#     def test_decorated(self):
#         values1 = []
#         values2 = []
#         values3 = []
#         values4 = []
#
#         def callback():
#             w = Widget()
#
#             w.values.clear()
#             w.control1.valueChanged[int].emit(12)
#             w.control1.valueChanged[str].emit('ha')
#             values1[:] = w.values
#
#             w.values.clear()
#             w.control2.valueChanged[int].emit(12)
#             w.control2.valueChanged[str].emit('ha')
#             values2[:] = w.values
#
#             w.values.clear()
#             w.control3.valueChanged[int].emit(12)
#             w.control3.valueChanged[str].emit('ha')
#             values3[:] = w.values
#
#             w.values.clear()
#             w.control4.valueChanged[int].emit(12)
#             w.control4.valueChanged[str].emit('ha')
#             values4[:] = w.values
#
#             self.app.quit()
#
#         with using_asyncio_from_qt():
#             QtCore.QTimer.singleShot(0, callback)
#             if hasattr(self.app, "exec"):
#                 self.app.exec()
#             else:
#                 self.app.exec_()
#
#         if is_pyqt:
#             self.assertEqual(values1, ["control1", 12, "control1", "ha"])
#         else:
#             self.assertEqual(values1, [])
#         self.assertEqual(values2, ["control2", 12])
#         if is_pyqt:
#             self.assertEqual(values3, ["control3", 12, "control3", "ha"])
#         else:
#             self.assertEqual(values3, [])
#         self.assertEqual(values4, ["control4", "ha"])


if __name__ == '__main__':
    unittest.main()

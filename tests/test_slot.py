""" test_slot.py - test the asyncslot() function """

import asyncio
import sys
import unittest
from shim import QtCore
from qtinter import asyncslot, using_asyncio_from_qt


is_pyqt = QtCore.__name__.startswith('PyQt')

if is_pyqt:
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
else:
    Signal = QtCore.Signal
    Slot = QtCore.Slot


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

qc = QtCore.Qt.ConnectionType.QueuedConnection

qt_slot_supports_descriptor = not QtCore.__name__.startswith('PyQt')


class TestMixin:
    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def _test_slot(self, slot):

        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(0, loop.quit)

        sender = SenderObject()
        sender.signal.connect(slot, QtCore.Qt.ConnectionType.QueuedConnection)
        sender.signal.emit(True)

        called.clear()
        with using_asyncio_from_qt():
            if hasattr(loop, 'exec'):
                loop.exec()
            else:
                loop.exec_()
        return called.copy()


# =============================================================================
# Tests on free function as slot
# =============================================================================

async def afunc():
    visit('afunc.1')
    await asyncio.sleep(0)
    visit('afunc.2')


@Slot()
async def slot_afunc():
    visit('slot_afunc.1')
    await asyncio.sleep(0)
    visit('slot_afunc.2')


@asyncslot
async def decorated_afunc():
    visit('decorated_afunc.1')
    await asyncio.sleep(0)
    visit('decorated_afunc.2')


@Slot()
@asyncslot
async def slot_decorated_afunc():
    visit('slot_decorated_afunc.1')
    await asyncio.sleep(0)
    visit('slot_decorated_afunc.2')


@asyncslot
@Slot()
async def decorated_slot_afunc():
    visit('decorated_slot_afunc.1')
    await asyncio.sleep(0)
    visit('decorated_slot_afunc.2')


class TestFreeFunction(TestMixin, unittest.TestCase):

    # -------------------------------------------------------------------------
    # Test async free function without Slot decoration
    # -------------------------------------------------------------------------

    def test_wrapped_afunc(self):
        result = self._test_slot(asyncslot(afunc))
        self.assertEqual(result, ['afunc.1', 'afunc.2'])

    def test_decorated_afunc(self):
        result = self._test_slot(decorated_afunc)
        self.assertEqual(result, ['decorated_afunc.1', 'decorated_afunc.2'])

    # -------------------------------------------------------------------------
    # Test async free function with Slot decoration
    # -------------------------------------------------------------------------

    def test_wrapped_slot_afunc(self):
        self.assertEqual(self._test_slot(asyncslot(slot_afunc)),
                         ['slot_afunc.1', 'slot_afunc.2'])

    def test_decorated_slot_afunc(self):
        self.assertEqual(self._test_slot(decorated_slot_afunc),
                         ['decorated_slot_afunc.1', 'decorated_slot_afunc.2'])

    def test_slot_decorated_afunc(self):
        self.assertEqual(self._test_slot(slot_decorated_afunc),
                         ['slot_decorated_afunc.1', 'slot_decorated_afunc.2'])

    # -------------------------------------------------------------------------
    # Test wrapped free function that's not apparently a coroutine function
    # -------------------------------------------------------------------------

    def test_wrapped_afunc_indirect(self):
        self.assertEqual(self._test_slot(asyncslot(lambda: afunc())),
                         ['afunc.1', 'afunc.2'])

    # -------------------------------------------------------------------------
    # Test invalid arguments to asyncslot
    # -------------------------------------------------------------------------

    def test_invalid_argument_type(self):
        with self.assertRaises(TypeError):
            asyncslot(afunc())

    def _test_excess_arguments(self, f):
        # Slot requires more arguments than signal provides
        error = None

        def g(*args, **kwargs):
            nonlocal error
            try:
                asyncslot(f)(*args, **kwargs)
            except BaseException as exc:
                error = exc

        self._test_slot(g)
        self.assertIsInstance(error, TypeError)

    def test_excess_regular_arguments(self):
        async def f(a, b): pass
        self._test_excess_arguments(f)

    @unittest.skipIf(sys.version_info < (3, 8), "requires Python >= 3.8")
    def test_excess_positional_arguments(self):
        local_vars = dict()
        exec("async def f(a, b, /): pass", globals(), local_vars)
        self._test_excess_arguments(local_vars["f"])

    def test_keyword_only_arguments_without_default(self):
        async def f(*, a): pass
        async def g(*args, a): pass
        with self.assertRaises(TypeError):
            asyncslot(f)
        with self.assertRaises(TypeError):
            asyncslot(g)

    def test_keyword_only_arguments_with_default(self):
        async def f(*, a=10):
            called.append(a)

        async def g(*args, a=20):
            called.append(len(args))
            called.append(a)

        self.assertEqual(self._test_slot(asyncslot(f)), [10])
        self.assertEqual(self._test_slot(asyncslot(g)), [1, 20])

    def test_var_keyword_arguments(self):
        async def f(**kwargs):
            called.append(len(kwargs))

        self.assertEqual(self._test_slot(asyncslot(f)), [0])

    # -------------------------------------------------------------------------
    # Test running asyncslot without a loop or with an incompatible loop
    # -------------------------------------------------------------------------

    def test_no_loop(self):
        async def f(): pass
        with self.assertRaisesRegex(RuntimeError, 'without'):
            asyncslot(f)()

    def test_incompatible_loop(self):
        async def f():
            asyncslot(f)()
        with self.assertRaisesRegex(RuntimeError, 'compatible'):
            asyncio.run(f())


# =============================================================================
# Tests on methods as slot
# =============================================================================

class Receiver:
    secret = 'Cls'

    def __init__(self):
        super().__init__()  # needed for cooperative multiple inheritance
        self.secret = 'Self'

    # -------------------------------------------------------------------------
    # Instance method
    # -------------------------------------------------------------------------

    async def amethod(self):
        visit('amethod.1', self)
        await asyncio.sleep(0)
        visit('amethod.2', self)

    @asyncslot
    async def decorated_amethod(self):
        visit('decorated_amethod.1', self)
        await asyncio.sleep(0)
        visit('decorated_amethod.2', self)

    @Slot()
    async def slot_amethod(self):
        visit('slot_amethod.1', self)
        await asyncio.sleep(0)
        visit('slot_amethod.2', self)

    @Slot()
    @asyncslot
    async def slot_decorated_amethod(self):
        visit('slot_decorated_amethod.1', self)
        await asyncio.sleep(0)
        visit('slot_decorated_amethod.2', self)

    @asyncslot
    @Slot()
    async def decorated_slot_amethod(self):
        visit('decorated_slot_amethod.1', self)
        await asyncio.sleep(0)
        visit('decorated_slot_amethod.2', self)

    # -------------------------------------------------------------------------
    # Class method
    # -------------------------------------------------------------------------

    @classmethod
    async def class_amethod(cls):
        visit('class_amethod.1', cls)
        await asyncio.sleep(0)
        visit('class_amethod.2', cls)

    @classmethod
    @asyncslot
    async def class_decorated_amethod(cls):
        visit('class_decorated_amethod.1', cls)
        await asyncio.sleep(0)
        visit('class_decorated_amethod.2', cls)

    # TODO: slot_class_amethod, class_slot_amethod,
    # TODO: slot_class_decorated_amethod, class_slot_decorated_amethod,
    # TODO: class_decorated_slot_amethod

    # -------------------------------------------------------------------------
    # Static method
    # -------------------------------------------------------------------------

    @staticmethod
    async def static_amethod():
        visit('static_amethod.1')
        await asyncio.sleep(0)
        visit('static_amethod.2')

    @staticmethod
    @asyncslot
    async def static_decorated_amethod():
        visit('static_decorated_amethod.1')
        await asyncio.sleep(0)
        visit('static_decorated_amethod.2')

    # TODO: slot_static_amethod, static_slot_amethod,
    # TODO: slot_static_decorated_amethod, static_slot_decorated_amethod,
    # TODO: static_decorated_slot_amethod


class ReceiverObject(Receiver, QtCore.QObject):
    pass


class TestReceiverObject(TestMixin, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.receiver = ReceiverObject()

    def tearDown(self):
        self.receiver = None
        super().tearDown()

    # -------------------------------------------------------------------------
    # Test instance method
    # -------------------------------------------------------------------------

    def test_wrapped_amethod(self):
        self.assertEqual(self._test_slot(asyncslot(self.receiver.amethod)),
                         ['amethod.1(Self)', 'amethod.2(Self)'])

    def test_decorated_amethod(self):
        self.assertEqual(
            self._test_slot(self.receiver.decorated_amethod),
            ['decorated_amethod.1(Self)', 'decorated_amethod.2(Self)'])

    def test_wrapped_slot_amethod(self):
        self.assertEqual(
            self._test_slot(asyncslot(self.receiver.slot_amethod)),
            ['slot_amethod.1(Self)', 'slot_amethod.2(Self)'])

    def test_decorated_slot_amethod(self):
        self.assertEqual(
            self._test_slot(self.receiver.decorated_slot_amethod),
            ['decorated_slot_amethod.1(Self)', 'decorated_slot_amethod.2(Self)'])

    def test_slot_decorated_amethod(self):
        self.assertEqual(
            self._test_slot(self.receiver.slot_decorated_amethod),
            ['slot_decorated_amethod.1(Self)', 'slot_decorated_amethod.2(Self)'])

    # -------------------------------------------------------------------------
    # Test class method
    # -------------------------------------------------------------------------

    def test_wrapped_class_amethod(self):
        self.assertEqual(
            self._test_slot(asyncslot(self.receiver.class_amethod)),
            ['class_amethod.1(Cls)', 'class_amethod.2(Cls)'])

    def test_class_decorated_amethod(self):
        self.assertEqual(
            self._test_slot(self.receiver.class_decorated_amethod),
            ['class_decorated_amethod.1(Cls)', 'class_decorated_amethod.2(Cls)'])

    # -------------------------------------------------------------------------
    # Test static method
    # -------------------------------------------------------------------------

    def test_wrapped_static_amethod(self):
        self.assertEqual(
            self._test_slot(asyncslot(self.receiver.static_amethod)),
            ['static_amethod.1', 'static_amethod.2'])

    def test_static_decorated_amethod(self):
        self.assertEqual(
            self._test_slot(self.receiver.static_decorated_amethod),
            ['static_decorated_amethod.1', 'static_decorated_amethod.2'])


class TestReceiver(TestReceiverObject):
    def setUp(self):
        super().setUp()
        self.receiver = Receiver()

    @unittest.skipIf(is_pyqt, "not supported by PyQt")
    def test_slot_decorated_amethod(self):
        super().test_slot_decorated_amethod()

    @unittest.skipIf(is_pyqt, "not supported by PyQt")
    def test_decorated_slot_amethod(self):
        super().test_decorated_slot_amethod()


# =============================================================================
# Test misc slot behavior
# =============================================================================


class IntSender(QtCore.QObject):
    signal = Signal(int)


class IntReceiver:
    def __init__(self, output):
        self.output = output

    async def original_slot(self, v):
        self.output[0] += v

    @asyncslot
    async def decorated_slot(self, v):
        self.output[0] *= v


class StrongReceiver:
    __slots__ = 'output',

    def __init__(self, output):
        self.output = output

    def method(self, v):
        self.output[0] -= v

    async def amethod(self, v):
        self.output[0] += v

    @asyncslot
    async def decorated_amethod(self, v):
        self.output[0] *= v


class TestSlotBehavior(unittest.TestCase):

    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def test_weak_reference_decorated(self):
        # Connection with bounded decorated method holds weak reference.
        output = [1]
        sender = IntSender()
        receiver = IntReceiver(output)
        with using_asyncio_from_qt():
            sender.signal.connect(receiver.decorated_slot)
            sender.signal.emit(3)
            self.assertEqual(output[0], 3)
            receiver = None
            sender.signal.emit(5)
            # expecting no change, because connection should have been deleted
            self.assertEqual(output[0], 3)

    def test_weak_reference_wrapped(self):
        # Wrapping a bounded method holds strong reference to the receiver
        # object.
        output = [1]
        sender = IntSender()
        receiver = IntReceiver(output)
        with using_asyncio_from_qt():
            sender.signal.connect(asyncslot(receiver.original_slot))
            sender.signal.emit(3)
            self.assertEqual(output[0], 4)
            receiver = None
            sender.signal.emit(5)
            # expecting change, because connection is still alive
            self.assertEqual(output[0], 4)

    def test_weak_reference_wrapped_2(self):
        # Keeping a (strong) reference to wrapped asyncslot keeps the
        # underlying method alive (similar to keeping a strong reference
        # to the underlying method).
        output = [1]
        sender = IntSender()
        receiver = IntReceiver(output)
        with using_asyncio_from_qt():
            the_slot = asyncslot(receiver.original_slot)
            sender.signal.connect(the_slot)
            # TODO: test disconnect(the_slot)
            sender.signal.emit(3)
            self.assertEqual(output[0], 4)
            receiver = None
            sender.signal.emit(5)
            # The slot should still be invoked because the_slot keeps it alive.
            self.assertEqual(output[0], 9)
            the_slot = None
            sender.signal.emit(6)
            # The slot should no longer be called
            self.assertEqual(output[0], 9)

    def test_strong_reference(self):
        # Wrapping a method in partial keeps the receiver object alive.
        # This test also tests that functools.partial() is supported.
        import functools

        output = [1]
        sender = IntSender()
        receiver = IntReceiver(output)
        with using_asyncio_from_qt():
            sender.signal.connect(
                asyncslot(functools.partial(receiver.original_slot)))
            sender.signal.emit(3)
            self.assertEqual(output[0], 4)
            receiver = None
            sender.signal.emit(5)
            # expecting change, because connection is still alive
            self.assertEqual(output[0], 9)

    def test_await(self):
        # asyncslot returns a Task object and so can be awaited.

        counter = 0

        @asyncslot
        async def work():
            await asyncio.sleep(0.1)
            return 1

        async def entry():
            nonlocal counter
            for _ in range(5):
                await work()
                counter += 1
            loop.quit()

        QtCore.QTimer.singleShot(0, asyncslot(entry))

        with using_asyncio_from_qt():
            loop = QtCore.QEventLoop()
            if hasattr(loop, 'exec'):
                loop.exec()
            else:
                loop.exec_()

        self.assertEqual(counter, 5)

    def test_strong_receiver(self):
        # Test connecting to a bounded method of an object that does not
        # support weak reference.
        output = [1]
        sender = IntSender()
        receiver = StrongReceiver(output)
        with using_asyncio_from_qt():
            with self.assertRaises(SystemError if is_pyqt else TypeError):
                sender.signal.connect(receiver.method)
            with self.assertRaises(SystemError if is_pyqt else TypeError):
                sender.signal.connect(receiver.decorated_amethod)
            with self.assertRaises(TypeError):
                sender.signal.connect(asyncslot(receiver.amethod))


# =============================================================================
# Test signal override by parameter type
# =============================================================================

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

    @asyncslot
    @Slot(int)
    async def on_control1_valueChanged(self, newValue):
        self.values.append("control1")
        self.values.append(newValue)

    @Slot(str)
    @asyncslot
    async def on_control2_valueChanged(self, newValue):
        self.values.append("control2")
        self.values.append(newValue)

    @asyncslot
    async def on_control3_valueChanged(self, newValue):
        self.values.append("control3")
        self.values.append(newValue)

    @Slot(int)
    @asyncslot
    @Slot(str)
    async def on_control4_valueChanged(self, newValue):
        self.values.append("control4")
        self.values.append(newValue)


class TestSlotSelection(unittest.TestCase):
    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

    def tearDown(self):
        self.app = None

    def test_decorated(self):
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

            self.app.quit()

        with using_asyncio_from_qt():
            QtCore.QTimer.singleShot(0, callback)
            if hasattr(self.app, "exec"):
                self.app.exec()
            else:
                self.app.exec_()

        self.assertEqual(values1, ["control1", 12])
        self.assertEqual(values2, ["control2", "ha"])
        if is_pyqt:
            self.assertEqual(values3, ["control3", 12, "control3", "ha"])
        else:
            self.assertEqual(values3, [])
        self.assertEqual(values4, ["control4", 12, "control4", "ha"])


if __name__ == '__main__':
    # TODO: insert sync callback to check invocation order
    unittest.main()

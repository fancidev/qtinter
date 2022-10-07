""" test_slot.py - test the asyncslot() function """

import asyncio
import unittest
from shim import QtCore
from qtinter import asyncslot, using_asyncio_from_qt


called = []


def visit(s, tag=None):
    if tag is not None:
        msg = f'{s}({tag.secret})'
    else:
        msg = s
    # print(msg)
    called.append(msg)


class MySignalObject(QtCore.QObject):
    ready0 = QtCore.Signal()
    ready1 = QtCore.Signal(bool)


class MySlotMixin:
    pass


qt_slot_supports_descriptor = not QtCore.__name__.startswith('PyQt')


class MySlotObject(QtCore.QObject):
    secret = 'Cls'

    def __init__(self):
        super().__init__()
        self.secret = 'Self'

    # -------------------------------------------------------------------------
    # Instance method
    # -------------------------------------------------------------------------

    def method(self):
        visit('method', self)

    @QtCore.Slot()
    def slot_method(self):
        visit('slot_method', self)

    async def amethod(self):
        visit('amethod.1', self)
        await asyncio.sleep(0)
        visit('amethod.2', self)

    @QtCore.Slot()
    async def slot_amethod(self):
        visit('slot_amethod.1', self)
        await asyncio.sleep(0)
        visit('slot_amethod.2', self)

    @asyncslot
    async def decorated_amethod(self):
        visit('decorated_amethod.1', self)
        await asyncio.sleep(0)
        visit('decorated_amethod.2', self)

    @QtCore.Slot()
    @asyncslot
    async def slot_decorated_amethod(self):
        visit('slot_decorated_amethod.1', self)
        await asyncio.sleep(0)
        visit('slot_decorated_amethod.2', self)

    @asyncslot
    @QtCore.Slot()
    async def decorated_slot_amethod(self):
        visit('decorated_slot_amethod.1', self)
        await asyncio.sleep(0)
        visit('decorated_slot_amethod.2', self)

    # -------------------------------------------------------------------------
    # Class method
    # -------------------------------------------------------------------------

    @classmethod
    def class_method(cls):
        visit('class_method', cls)

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

    # Not supported
    # @asyncslot
    # @classmethod
    # async def class_decorated_amethod(cls):
    #     visit('class_decorated_amethod.1', cls)
    #     await asyncio.sleep(0)
    #     visit('class_decorated_amethod.2', cls)

    if qt_slot_supports_descriptor:

        @QtCore.Slot()
        @classmethod
        def slot_class_method(cls):
            visit('slot_class_method', cls)

        @classmethod
        @QtCore.Slot()
        def class_slot_method(cls):
            visit('class_slot_method', cls)


    # -------------------------------------------------------------------------
    # Static method
    # -------------------------------------------------------------------------

    @staticmethod
    def static_method():
        visit('static_method')

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

    if qt_slot_supports_descriptor:

        @QtCore.Slot()
        @staticmethod
        def slot_static_method():
            visit('slot_static_method')

        @staticmethod
        @QtCore.Slot()
        def static_slot_method():
            visit('static_slot_method')


def func():
    visit('func')


@QtCore.Slot()
def slot_func():
    visit('slot_func')


async def afunc():
    visit('afunc.1')
    await asyncio.sleep(0)
    visit('afunc.2')


@asyncslot
async def decorated_afunc():
    visit('decorated_afunc.1')
    await asyncio.sleep(0)
    visit('decorated_afunc.2')


@QtCore.Slot()
async def slot_afunc():
    visit('slot_afunc.1')
    await asyncio.sleep(0)
    visit('slot_afunc.2')


@QtCore.Slot()
@asyncslot
async def slot_decorated_afunc():
    visit('slot_decorated_afunc.1')
    await asyncio.sleep(0)
    visit('slot_decorated_afunc.2')


@asyncslot
@QtCore.Slot()
async def decorated_slot_afunc():
    visit('decorated_slot_afunc.1')
    await asyncio.sleep(0)
    visit('decorated_slot_afunc.2')


qc = QtCore.Qt.ConnectionType.QueuedConnection


class TestSlot(unittest.TestCase):

    def setUp(self) -> None:
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])

        self.qt_loop = QtCore.QEventLoop()
        self.receiver = MySlotObject()
        self.sender = MySignalObject()
        self.signal = self.sender.ready1
        self.connection = None

    def tearDown(self) -> None:
        if self.connection is not None:
            self.signal.disconnect()
            self.connection = None
        self.sender = None
        self.receiver = None
        self.qt_loop = None
        self.app = None

    def _run_once(self):
        QtCore.QTimer.singleShot(0, self.qt_loop.quit)
        self.signal.emit(True)

        called.clear()
        with using_asyncio_from_qt():
            if hasattr(self.qt_loop, 'exec'):
                self.qt_loop.exec()
            else:
                self.qt_loop.exec_()
        return called.copy()

    # -------------------------------------------------------------------------
    # Test non-async free function without Qt.Slot decoration
    # -------------------------------------------------------------------------

    def test_func(self):
        # Qt sanity check
        self.connection = self.signal.connect(func, qc)
        result = self._run_once()
        self.assertEqual(result, ['func'])

    def test_wrapped_func(self):
        # Wrapping a func is an error
        with self.assertRaises(TypeError):
            asyncslot(func)

    def test_decorated_func(self):
        # Decorating a func is an error
        with self.assertRaises(TypeError):
            @asyncslot
            def fn():
                pass

    # -------------------------------------------------------------------------
    # Test non-async free function with Qt.Slot decoration
    # -------------------------------------------------------------------------

    def test_slot_func(self):
        # Qt sanity check
        self.connection = self.signal.connect(slot_func, qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_func'])

    def test_wrapped_slot_func(self):
        # Wrapping a func is an error
        with self.assertRaises(TypeError):
            asyncslot(slot_func)

    def test_decorated_slot_func(self):
        # Decorating a func is an error
        with self.assertRaises(TypeError):
            @asyncslot
            @QtCore.Slot()
            def fn():
                pass

    # -------------------------------------------------------------------------
    # Test async free function without Qt.Slot decoration
    # -------------------------------------------------------------------------

    def test_wrapped_afunc(self):
        # Test wrapping afunc
        self.connection = self.signal.connect(asyncslot(afunc), qc)
        result = self._run_once()
        self.assertEqual(result, ['afunc.1', 'afunc.2'])

    def test_decorated_afunc(self):
        # Test decorating afunc
        self.connection = self.signal.connect(decorated_afunc, qc)
        result = self._run_once()
        self.assertEqual(result, ['decorated_afunc.1', 'decorated_afunc.2'])

    def test_wrapped_decorated_afunc(self):
        # Wrapping a decorated afunc is an error
        with self.assertRaises(TypeError):
            asyncslot(decorated_afunc)

    # -------------------------------------------------------------------------
    # Test async free function with Qt.Slot decoration
    # -------------------------------------------------------------------------

    def test_wrapped_slot_afunc(self):
        # Test wrapping slot_afunc
        self.connection = self.signal.connect(asyncslot(slot_afunc), qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_afunc.1', 'slot_afunc.2'])

    def test_decorated_slot_afunc(self):
        self.connection = self.signal.connect(decorated_slot_afunc, qc)
        result = self._run_once()
        self.assertEqual(result, ['decorated_slot_afunc.1',
                                  'decorated_slot_afunc.2'])

    def test_slot_decorated_afunc(self):
        self.connection = self.signal.connect(slot_decorated_afunc, qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_decorated_afunc.1',
                                  'slot_decorated_afunc.2'])

    # -------------------------------------------------------------------------
    # Test non-async method
    # -------------------------------------------------------------------------

    def test_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(self.receiver.method, qc)
        result = self._run_once()
        self.assertEqual(result, ['method(Self)'])

    def test_wrapped_method(self):
        # Wrapping a method is an error
        with self.assertRaises(TypeError):
            asyncslot(self.receiver.method)

    def test_slot_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(self.receiver.slot_method, qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_method(Self)'])

    def test_wrapped_slot_method(self):
        # Wrapping a method is an error
        with self.assertRaises(TypeError):
            asyncslot(self.receiver.slot_method)

    # -------------------------------------------------------------------------
    # Test async method
    # -------------------------------------------------------------------------

    def test_wrapped_amethod(self):
        self.connection = self.signal.connect(
            asyncslot(self.receiver.amethod), qc)
        result = self._run_once()
        self.assertEqual(result, ['amethod.1(Self)', 'amethod.2(Self)'])

    def test_decorated_amethod(self):
        self.connection = self.signal.connect(
            self.receiver.decorated_amethod, qc)
        result = self._run_once()
        self.assertEqual(result, ['decorated_amethod.1(Self)',
                                  'decorated_amethod.2(Self)'])

    def test_wrapped_decorated_amethod(self):
        with self.assertRaises(TypeError):
            asyncslot(self.receiver.decorated_amethod)

    def test_wrapped_slot_amethod(self):
        self.connection = self.signal.connect(
            asyncslot(self.receiver.slot_amethod), qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_amethod.1(Self)',
                                  'slot_amethod.2(Self)'])

    def test_decorated_slot_amethod(self):
        self.connection = self.signal.connect(
            self.receiver.decorated_slot_amethod, qc)
        result = self._run_once()
        self.assertEqual(result, ['decorated_slot_amethod.1(Self)',
                                  'decorated_slot_amethod.2(Self)'])

    def test_slot_decorated_amethod(self):
        self.connection = self.signal.connect(
            self.receiver.slot_decorated_amethod, qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_decorated_amethod.1(Self)',
                                  'slot_decorated_amethod.2(Self)'])

    # -------------------------------------------------------------------------
    # Test non-async class method
    # -------------------------------------------------------------------------

    def test_class_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(self.receiver.class_method, qc)
        result = self._run_once()
        self.assertEqual(result, ['class_method(Cls)'])

    def test_wrapped_class_method(self):
        with self.assertRaises(TypeError):
            asyncslot(self.receiver.class_method)

    @unittest.skipUnless(qt_slot_supports_descriptor, 'not supported by PyQt')
    def test_slot_class_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(
            self.receiver.slot_class_method, qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_class_method(Cls)'])

    @unittest.skipUnless(qt_slot_supports_descriptor, 'not supported by PyQt')
    def test_class_slot_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(
            self.receiver.class_slot_method, qc)
        result = self._run_once()
        self.assertEqual(result, ['class_slot_method(Cls)'])

    # -------------------------------------------------------------------------
    # Test async class method
    # -------------------------------------------------------------------------

    def test_wrapped_class_amethod(self):
        self.connection = self.signal.connect(
            asyncslot(self.receiver.class_amethod), qc)
        result = self._run_once()
        self.assertEqual(result, ['class_amethod.1(Cls)',
                                  'class_amethod.2(Cls)'])

    def test_class_decorated_amethod(self):
        self.connection = self.signal.connect(
            self.receiver.class_decorated_amethod, qc)
        result = self._run_once()
        self.assertEqual(result, ['class_decorated_amethod.1(Cls)',
                                  'class_decorated_amethod.2(Cls)'])

    # -------------------------------------------------------------------------
    # Test non-async static method
    # -------------------------------------------------------------------------

    def test_static_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(self.receiver.static_method, qc)
        result = self._run_once()
        self.assertEqual(result, ['static_method'])

    def test_wrapped_static_method(self):
        with self.assertRaises(TypeError):
            asyncslot(self.receiver.static_method)

    @unittest.skipUnless(qt_slot_supports_descriptor, 'not supported by PyQt')
    def test_slot_static_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(
            self.receiver.slot_static_method, qc)
        result = self._run_once()
        self.assertEqual(result, ['slot_static_method'])

    @unittest.skipUnless(qt_slot_supports_descriptor, 'not supported by PyQt')
    def test_static_slot_method(self):
        # Qt sanity check
        self.connection = self.signal.connect(
            self.receiver.static_slot_method, qc)
        result = self._run_once()
        self.assertEqual(result, ['static_slot_method'])

    # -------------------------------------------------------------------------
    # Test async static method
    # -------------------------------------------------------------------------

    def test_wrapped_static_amethod(self):
        self.connection = self.signal.connect(
            asyncslot(self.receiver.static_amethod), qc)
        result = self._run_once()
        self.assertEqual(result, ['static_amethod.1', 'static_amethod.2'])

    def test_static_decorated_amethod(self):
        self.connection = self.signal.connect(
            self.receiver.static_decorated_amethod, qc)
        result = self._run_once()
        self.assertEqual(result, ['static_decorated_amethod.1',
                                  'static_decorated_amethod.2'])


if __name__ == '__main__':
    # TODO: insert sync callback to check invocation order
    unittest.main()

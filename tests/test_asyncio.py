import asyncio
from test.test_asyncio.test_base_events import (
    BaseEventLoopTests, BaseEventLoopWithSelectorTests, RunningLoopTests,
    BaseLoopSockSendfileTests,
)
from shim import QtCore
from asyncslot._base_events import AsyncSlotBaseEventLoop
from asyncslot._selector_events import AsyncSlotSelectorEventLoop
from asyncslot import AsyncSlotDefaultEventLoopPolicy
from unittest import mock
import unittest


class _Mixin:
    def setUp(self):
        if QtCore.QCoreApplication.instance() is not None:
            self.app = QtCore.QCoreApplication.instance()
        else:
            self.app = QtCore.QCoreApplication([])
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.app = None


class MyBaseEventLoopTests(_Mixin, BaseEventLoopTests):
    def setUp(self):
        super().setUp()
        self.loop = AsyncSlotBaseEventLoop()
        self.loop._selector = mock.Mock()
        self.loop._selector.select.return_value = ()
        self.set_event_loop(self.loop)


class MyBaseEventLoopWithSelectorTests(_Mixin, BaseEventLoopWithSelectorTests):
    def setUp(self):
        super().setUp()
        self.loop = AsyncSlotSelectorEventLoop()
        self.set_event_loop(self.loop)


class MyRunningLoopTests(_Mixin, RunningLoopTests):
    def setUp(self):
        super().setUp()
        asyncio.set_event_loop_policy(AsyncSlotDefaultEventLoopPolicy())

    def tearDown(self):
        asyncio.set_event_loop_policy(None)
        super().tearDown()


class MyBaseLoopSockSendfileTests(_Mixin, BaseLoopSockSendfileTests):
    def setUp(self):
        super().setUp()
        self.loop = AsyncSlotSelectorEventLoop()  # TODO: need BaseSelectorEventLoop
        self.set_event_loop(self.loop)

    def test__sock_sendfile_native_failure(self):
        pass

    def test_sock_sendfile_no_fallback(self):
        pass


if __name__ == "__main__":
    unittest.main()

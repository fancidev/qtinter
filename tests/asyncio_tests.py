"""asyncio_tests.py - run Python bundled asyncio test suite

The test suite is located in Lib/test/test_asyncio.  Available test modules
under different Python versions are as follows:

Module                      3.7    3.8    3.9    3.10    3.11
-------------------------------------------------------------
test_base_events.py         ✓      ✓      ✓      ✓       ✓
test_buffered_proto.py      ✓      ✓      ✓      ✓       ✓
test_context.py             ✓      ✓      ✓      ✓       ✓
test_events.py              ✓      ✓      ✓      ✓       ✓
test_futures.py             ✓      ✓      ✓      ✓       ✓
test_locks.py               ✓      ✓      ✓      ✓       ✓
test_pep492.py              ✓      ✓      ✓      ✓       ✓
test_proactor_events.py     ✓      ✓      ✓      ✓       ✓
test_queues.py              ✓      ✓      ✓      ✓       ✓
test_runners.py             ✓      ✓      ✓      ✓       ✓
test_selector_events.py     ✓      ✓      ✓      ✓       ✓
test_server.py              ✓      ✓      ✓      ✓       ✓
test_sslproto.py            ✓      ✓      ✓      ✓       ✓
test_streams.py             ✓      ✓      ✓      ✓       ✓
test_subprocess.py          ✓      ✓      ✓      ✓       ✓
test_tasks.py               ✓      ✓      ✓      ✓       ✓
test_transports.py          ✓      ✓      ✓      ✓       ✓
test_unix_events.py         ✓      ✓      ✓      ✓       ✓
test_windows_events.py      ✓      ✓      ✓      ✓       ✓
test_windows_utils.py       ✓      ✓      ✓      ✓       ✓
test_asyncio_waitfor.py            ✓
test_futures2.py                   ✓      ✓      ✓       ✓
test_protocols.py                  ✓      ✓      ✓       ✓
test_sendfile.py                   ✓      ✓      ✓       ✓
test_sock_lowlevel.py              ✓      ✓      ✓       ✓
test_threads.py                           ✓      ✓       ✓
test_waitfor.py                           ✓      ✓       ✓
test_ssl.py                                              ✓
test_taskgroups.py                                       ✓
test_timeouts.py                                         ✓

"""
import sys

import asyncio
import asyncio.base_events
import asyncio.selector_events
import asyncio.proactor_events
if sys.platform == 'win32':
    import asyncio.windows_events
else:
    import asyncio.unix_events

import qtinter
import unittest

from qtinter.bindings import QtCore
app = QtCore.QCoreApplication([])

# We now need to monkey-patch asyncio ...

asyncio.BaseEventLoop = asyncio.base_events.BaseEventLoop = qtinter.QiBaseEventLoop
asyncio.selector_events.BaseSelectorEventLoop = qtinter.QiBaseSelectorEventLoop
asyncio.proactor_events.BaseProactorEventLoop = qtinter.QiBaseProactorEventLoop

if sys.platform == 'win32':
    asyncio.SelectorEventLoop = asyncio.windows_events.SelectorEventLoop = asyncio.windows_events._WindowsSelectorEventLoop = qtinter.QiSelectorEventLoop
    asyncio.ProactorEventLoop = asyncio.windows_events.ProactorEventLoop = qtinter.QiProactorEventLoop
    asyncio.IocpProactor = asyncio.windows_events.IocpProactor = qtinter._windows_events._QiProactor
    asyncio.WindowsSelectorEventLoopPolicy = asyncio.windows_events.WindowsSelectorEventLoopPolicy = qtinter.QiSelectorEventLoopPolicy
    asyncio.WindowsProactorEventLoopPolicy = asyncio.windows_events.WindowsProactorEventLoopPolicy = qtinter.QiProactorEventLoopPolicy
    asyncio.DefaultEventLoopPolicy = asyncio.windows_events.DefaultEventLoopPolicy = qtinter.QiDefaultEventLoopPolicy
else:
    asyncio.SelectorEventLoop = asyncio.unix_events.SelectorEventLoop = asyncio.unix_events._UnixSelectorEventLoop = qtinter.QiSelectorEventLoop
    asyncio.DefaultEventLoopPolicy = asyncio.unix_events.DefaultEventLoopPolicy = asyncio.unix_events._UnixDefaultEventLoopPolicy = qtinter.QiDefaultEventLoopPolicy


# Now import the tests into __main__
from test.test_asyncio import load_tests

# The following test is expected to fail because the call stack is
# changed with a qtinter event loop implementation.  If the test passes,
# it means the monkey patching didn't work!
import test.test_asyncio.test_events
test.test_asyncio.test_events.HandleTests.test_handle_source_traceback = \
    unittest.expectedFailure(test.test_asyncio.test_events.HandleTests.test_handle_source_traceback)

# To run a particular test, import that test class, and specify
# TestClassName.test_name on the command line. For example:
# python asyncio_tests.py ProactorLoopCtrlC.test_ctrl_c

# TODO: why do we display warnings to stderr, but not asyncio?

if __name__ == "__main__":
    unittest.main()

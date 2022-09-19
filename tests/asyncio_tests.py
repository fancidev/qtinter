import sys

import asyncio
import asyncio.base_events
import asyncio.selector_events
# import asyncio.proactor_events
if sys.platform == 'win32':
    import asyncio.windows_events
else:
    import asyncio.unix_events

import asyncslot
import unittest

from asyncslot.bindings import QtCore
app = QtCore.QCoreApplication([])

# We now need to monkey-patch asyncio ...

asyncio.BaseEventLoop = asyncio.base_events.BaseEventLoop = asyncslot.AsyncSlotBaseEventLoop

asyncio.selector_events.BaseSelectorEventLoop = asyncslot.AsyncSlotBaseSelectorEventLoop
# TODO: AsyncSlotBaseProactorEventLoop
# asyncio.proactor_events.BaseProactorEventLoop = asyncslot.AsyncSlotProactorEventLoop

if sys.platform == 'win32':
    asyncio.SelectorEventLoop = asyncio.windows_events.SelectorEventLoop = asyncslot.AsyncSlotSelectorEventLoop
    asyncio.ProactorEventLoop = asyncio.windows_events.ProactorEventLoop = asyncslot.AsyncSlotProactorEventLoop
    asyncio.IocpProactor = asyncio.windows_events.IocpProactor = asyncslot.AsyncSlotProactor
    asyncio.DefaultEventLoopPolicy = asyncio.windows_events.DefaultEventLoopPolicy = asyncslot.AsyncSlotDefaultEventLoopPolicy
    asyncio.WindowsSelectorEventLoopPolicy = asyncio.windows_events.WindowsSelectorEventLoopPolicy = asyncslot.AsyncSlotSelectorEventLoopPolicy
    asyncio.WindowsProactorEventLoopPolicy = asyncio.windows_events.WindowsProactorEventLoopPolicy = asyncslot.AsyncSlotProactorEventLoopPolicy
else:
    asyncio.SelectorEventLoop = asyncio.unix_events.SelectorEventLoop = asyncslot.AsyncSlotSelectorEventLoop
    asyncio.DefaultEventLoopPolicy = asyncio.unix_events.DefaultEventLoopPolicy = asyncslot.AsyncSlotDefaultEventLoopPolicy

# Now import the tests into __main__
from test.test_asyncio.test_base_events import *
from test.test_asyncio.test_events import *
# from test.test_asyncio.test_selector_events import *
# from test.test_asyncio.test_proactor_events import *
# from test.test_asyncio.test_unix_events import *
# from test.test_asyncio.test_windows_events import *

# The following tests are expected to fail, so skip them.
HandleTests.test_handle_source_traceback = None

# TODO: why do we display warnings to stderr, but not asyncio?

if __name__ == "__main__":
    unittest.main(verbosity=1)

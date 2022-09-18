import sys

import asyncio
import asyncio.base_events
import asyncio.selector_events
if sys.platform == 'win32':
    import asyncio.windows_events
else:
    import asyncio.unix_events

import asyncslot
import unittest

from shim import QtCore
app = QtCore.QCoreApplication([])

# We now need to monkey-patch asyncio ...

asyncio.base_events.BaseEventLoop = asyncslot.AsyncSlotBaseEventLoop
asyncio.BaseEventLoop = asyncio.base_events.BaseEventLoop

asyncio.selector_events.BaseSelectorEventLoop = asyncslot.AsyncSlotBaseSelectorEventLoop

if sys.platform == 'win32':
    raise NotImplementedError
else:
    asyncio.unix_events.SelectorEventLoop = asyncslot.AsyncSlotSelectorEventLoop
    asyncio.unix_events.DefaultEventLoopPolicy = asyncslot.AsyncSlotSelectorEventLoopPolicy
    asyncio.SelectorEventLoop = asyncio.unix_events.SelectorEventLoop
    asyncio.DefaultEventLoopPolicy = asyncio.unix_events.DefaultEventLoopPolicy

# Now import the tests into __main__
from test.test_asyncio.test_base_events import *


# TODO: why do we display warnings to stderr, but not asyncio?

if __name__ == "__main__":
    unittest.main()

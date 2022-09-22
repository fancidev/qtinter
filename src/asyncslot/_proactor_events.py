""" _proactor_events.py - no-op counterpart to asyncio.BaseProactorEventLoop """

import asyncio.proactor_events
from ._base_events import *


__all__ = 'AsyncSlotBaseProactorEventLoop',


class AsyncSlotBaseProactorEventLoop(
    AsyncSlotBaseEventLoop,
    asyncio.proactor_events.BaseProactorEventLoop
):
    pass

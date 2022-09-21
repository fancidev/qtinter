""" _proactor_events.py - no-op counterpart to asyncio.BaseProactorEventLoop """

import asyncio.proactor_events
from ._base_events import *


__all__ = 'AsyncSlotBaseProactorEventLoop',


class AsyncSlotBaseProactorEventLoop(
    AsyncSlotBaseEventLoop,
    asyncio.proactor_events.BaseProactorEventLoop
):
    pass

    # def __init__(self, proactor, standalone=True):
    #     super().__init__(proactor, standalone=standalone)

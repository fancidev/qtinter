""" _proactor_events.py - no-op counterpart to asyncio.BaseProactorEventLoop """

import asyncio.proactor_events
from ._base_events import *


__all__ = 'QiBaseProactorEventLoop',


class QiBaseProactorEventLoop(
    QiBaseEventLoop,
    asyncio.proactor_events.BaseProactorEventLoop
):
    pass

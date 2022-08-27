""" _selector_events.py - AsyncSlot based on SelectorEventLoop """

import asyncio
import selectors
from typing import List, Optional, Tuple
from ._base_events import AsyncSlotBaseEventLoop


class AsyncSlotSelector(selectors.DefaultSelector):
    def __init__(self):
        super().__init__()

    def select(self, timeout: Optional[float] = None) \
            -> List[Tuple[selectors.SelectorKey, int]]:
        raise NotImplementedError


class AsyncSlotSelectorEventLoop(AsyncSlotBaseEventLoop,
                                 asyncio.SelectorEventLoop):

    def __init__(self):
        selector = AsyncSlotSelector()
        super().__init__(selector)

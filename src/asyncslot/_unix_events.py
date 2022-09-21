""" _unix_events.py - define default loop and policy under unix """

import sys

if sys.platform == 'win32':
    raise ImportError('unix only')


import asyncio.unix_events
from . import _selector_events


__all__ = (
    'AsyncSlotDefaultEventLoop',
    'AsyncSlotDefaultEventLoopPolicy',
    'AsyncSlotSelectorEventLoop',
    'AsyncSlotSelectorEventLoopPolicy',
)


class AsyncSlotSelectorEventLoop(
    _selector_events.AsyncSlotBaseSelectorEventLoop,
    asyncio.unix_events.SelectorEventLoop
):
    pass


class AsyncSlotSelectorEventLoopPolicy(
    asyncio.unix_events.DefaultEventLoopPolicy
):
    _loop_factory = AsyncSlotSelectorEventLoop


AsyncSlotDefaultEventLoopPolicy = AsyncSlotSelectorEventLoopPolicy
AsyncSlotDefaultEventLoop = AsyncSlotSelectorEventLoop

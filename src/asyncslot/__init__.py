"""Implements asyncio event loop based on Qt event loop.

The asyncio event loop class hierarchy is as follows:

class                             submodule        alias
------------------------------------------------------------------------------
BaseEventLoop                     base_events
  BaseSelectorEventLoop           selector_events
    _UnixSelectorEventLoop        unix_events      SelectorEventLoop [1]
    _WindowsSelectorEventLoop     windows_events   SelectorEventLoop [2,3]
  BaseProactorEventLoop           proactor_events
    ProactorEventLoop             windows_events
BaseDefaultEventLoopPolicy        events
  _UnixDefaultEventLoopPolicy     unix_events      DefaultEventLoopPolicy [1]
  WindowsSelectorEventLoopPolicy  windows_events   DefaultEventLoopPolicy [2]
  WindowsProactorEventLoopPolicy  windows_events   DefaultEventLoopPolicy [3]

[1] under unix
[2] under Windows, for Python 3.7
[3] under Windows, for Python 3.8 and above

For ease of reference and to facilitate testing, asyncslot's source code is
arrange in a similar structure:

class                               submodule         alias
------------------------------------------------------------------------------
AsyncSlotBaseEventLoop              _base_events
  AsyncSlotBaseSelectorEventLoop    _selector_events
    AsyncSlotSelectorEventLoop      _unix_events      AsyncSlotDefaultEventLoop [1]
    AsyncSlotSelectorEventLoop      _windows_events   AsyncSlotDefaultEventLoop [2]
  AsyncSlotBaseProactorEventLoop    _proactor_events
    AsyncSlotProactorEventLoop      _windows_events   AsyncSlotDefaultEventLoop [3]
(asyncio.events.BaseDefaultEventLoopPolicy)
  AsyncSlotSelectorEventLoopPolicy  _unix_events      AsyncSlotDefaultEventLoopPolicy [1]
  AsyncSlotSelectorEventLoopPolicy  _windows_events   AsyncSlotDefaultEventLoopPolicy [2]
  AsyncSlotProactorEventLoopPolicy  _windows_events   AsyncSlotDefaultEventLoopPolicy [3]

"""
import sys

from ._base_events import *
from ._selector_events import *
from ._proactor_events import *
from ._slot import *
from ._runners import *


__all__ = (
    _base_events.__all__ +
    _selector_events.__all__ +
    _proactor_events.__all__ +
    _slot.__all__ +
    _runners.__all__
)


if sys.platform == 'win32':
    from ._windows_events import *
    __all__ += _windows_events.__all__
else:
    from ._unix_events import *
    __all__ += _unix_events.__all__

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

For ease of reference and to facilitate testing, qtinter's source code is
arrange in a similar structure:

class                        submodule         alias
------------------------------------------------------------------------------
QiBaseEventLoop              _base_events
  QiBaseSelectorEventLoop    _selector_events
    QiSelectorEventLoop      _unix_events      QiDefaultEventLoop [1]
    QiSelectorEventLoop      _windows_events   QiDefaultEventLoop [2]
  QiBaseProactorEventLoop    _proactor_events
    QiProactorEventLoop      _windows_events   QiDefaultEventLoop [3]
(asyncio.events.BaseDefaultEventLoopPolicy)
  QiSelectorEventLoopPolicy  _unix_events      QiDefaultEventLoopPolicy [1]
  QiSelectorEventLoopPolicy  _windows_events   QiDefaultEventLoopPolicy [2]
  QiProactorEventLoopPolicy  _windows_events   QiDefaultEventLoopPolicy [3]

"""
import sys

from ._base_events import *
from ._selector_events import *
from ._proactor_events import *
from ._signal import *
from ._slot import *
from ._contexts import *


__all__ = (
    _base_events.__all__ +
    _selector_events.__all__ +
    _proactor_events.__all__ +
    _signal.__all__ +
    _slot.__all__ +
    _contexts.__all__
)


if sys.platform == 'win32':
    from ._windows_events import *
    __all__ += _windows_events.__all__
else:
    from ._unix_events import *
    __all__ += _unix_events.__all__

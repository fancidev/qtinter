# asyncslot

`asyncslot` is a Python module that allows you to use asyncio-based 
libraries in Python for Qt.

**IMPORTANT: THIS PROJECT IS WORK IN PROGRESS.  THIS README DESCRIBES THE 
SPECIFICATION BUT IS NOT IMPLEMENTED!**

## Synopsis

This module provides the `AsyncSlot` decorator, which decorates a coroutine 
function to make it usable as a Qt slot.

Example code snippet:

```Python
import asyncio
import PySide6
from asyncslot import AsyncSlot

# lines omitted

@AsyncSlot()
async def say_something():
    print('Hi')
    await asyncio.sleep(1)
    print('Bye')

# lines omitted
    
some_button.clicked.connect(say_something)
```

## Requirements

`asyncslot` runs with Python 3.8 and PySide6 under MacOS.  Additional Python 
version, Qt binding and OS may be supported in the future.

## Installation

```commandline
pip install asyncslot
```

The above does _not_ install the Qt bindings.  To install Qt bindings, you may

```commandline
pip install PySide6
```

## Details

`asyncslot` implements the asyncio `AbstractEventLoop` interface "hosted" 
within a Qt event loop, so that Python libraries written for asyncio can be 
used with a Python for Qt application.

### Running Modes

A coroutine may be launched in an `AsyncSlotEventLoop` in one of two modes: 
_non-blocking mode_ or _blocking mode_.

Call `AsyncSlotEventLoop.run_task` to start a coroutine in _non-blocking 
mode_.  `run_task` executes the coroutine until the first suspension 
point and schedules the remainder in the running Qt event loop for later.  
An `asyncio.Task` object representing the scheduled task is returned to
the caller.  This is the primary workflow for `asyncslot` as it
integrates asyncio-based coroutines seamlessly into an existing Qt app.

Call `asyncio.run` (or `AsyncSlotEventLoop.run_until_complete`) to run a 
coroutine in _blocking mode_.  This starts a (possibly nested) `QEventLoop` 
and blocks until it exits (when the coroutine completes).  This is the 
standard asyncio workflow and is convenient for unit testing, but it's not 
suitable for integration with an existing Qt app because nested event loops
are not recommended by Qt.

For either mode, a (global) `QCoreApplication` (or `QApplication` /
`QGuiApplication`) instance must exist before running the coroutine, as 
required by Qt.

### The `AsyncSlot` Decorator

`asyncslot.AsyncSlot` decorates a coroutine function (a function starting 
with `async def`) to make it usable as a Qt slot.  The decorator basically 
calls `AsyncSlotEventLoop.run_task` to execute the coroutine.

A coroutine function, whether decorated with `QtCore.Slot` or not, cannot be 
used in Qt's signal-slot mechanism because calling it returns a coroutine 
object instead of performing real work.  In addition, an asyncio-compatible 
event loop needs to be running to execute an asyncio-based coroutine.

The `asyncslot.AsyncSlot` decorator fills this gap by creating an 
`AsyncSlotEventLoop` on the fly (if one is not already running) and calls 
its `run_task` method with the coroutine object.  The body of the coroutine 
before the first suspension point is executed immediately and the remainder 
scheduled for later execution.

This works nicely with a common scenario where some work is expected to be 
performed immediately in response to a signal.  For example, consider an app 
where a user clicks a button to send a purchase order.  To prevent an 
eager user from sending duplicate orders by repeatedly clicking the 
button, the `clicked` handler disablss the button on entry.  For this to 
work correctly the code before the first suspension point must be executed 
synchronously.

A coroutine function decorated with `AsyncSlot` can be awaited from another 
coroutine as if it were not decorated, because `AsyncSlot()()` returns a 
future.  Awaiting a decorated coroutine is expected to behave the same way 
as awaiting a plain coroutine; please report an issue if it does not.


### Cancellation

To cancel the running coroutine from within itself, raise 
`asyncio.CancelledError`.

To retrieve the task object from within the running coroutine so that it may 
be stored somewhere and cancelled externally later, call
`asyncio.current_task()` from within the running coroutine.

To retrieve the task object from outside the coroutine, use the return value 
of `run_task` (or `AsyncSlot`).


## Implementation Notes

By embedding a (logical) asyncio event loop inside a (physical) Qt event 
loop, what's not changed (from the perspective of the asyncio event loop) is 
that all calls (other than `call_soon_threadsafe`) are still made from the 
same thread.  This frees us from multi-threading complexities.

What has changed, however, is that in a standalone asyncio event loop, no 
code can be run when the schedular (specifically, `_run_once`) is blocked in 
`select()`, while in an embedded asyncio event loop, a `select()` call 
that would otherwise block yields, allowing any code to run while the loop 
is "logically" blocked in `select`.

For example, `BaseEventLoop.stop()` is implemented by setting the flag 
`_stopping` to `True`, which is then checked before the next iteration of
`_run_once` to stop the loop.  This works because `stop` can only ever be
called from a callback, and a callback can only ever be called after
`select` returns and before the next iteration of `_run_once`.  The behavior 
changes if `select` yields and `stop` is called -- the event loop wait not 
wake up until some IO is available.

We refer to code that runs (from the Qt event loop) after `select` yields 
and before `_run_once` is called again as _foreign code_.  We must examine 
and handle the implications of such foreign code.

We do this by fitting foreign code execution into the standalone asyncio
event loop model.  Specifically, we treat foreign code as if they were 
scheduled with `call_soon_threadsafe`, which wakes up the selector and
executes the code.  _With_ some loss of generality, we assume no IO event
nor timed callback is ready at the exact same time, so that the scheduler 
will be put back into blocking `select` immediately after the code finishes 
running (unless the code calls `stop`).  This simplification is acceptable
because the precise timing of multiple IO or timer events should never be 
relied upon.

In practice, we cannot actually wake up the asyncio scheduler every time 
foreign code is executed, firstly because there's no way to hook to every Qt 
callback and secondly because doing so would be highly inefficient. 
Instead, we _assume_ that foreign code that does not access the event loop
object or its selector is benign enough to be treated as _independent_
from the asyncio event loop ecosystem and may be safely ignored.

This leaves us to just consider foreign code that accesses the event loop 
object or its selector and examine its impact on scheduling.  The scheduler
depends on three things:  the `_ready` queue for "soon" callbacks, the 
`_scheduled` queue for timer callbacks, and `_selector` for IO events.
If the foreign code modifies any of these things, it needs to be handled.

While the public interface of `AbstractEventLoop` has numerous methods, the 
methods that modify those three things boil down to `call_soon`, `call_at`, 
`call_later`, (arguably) `stop`, and anything that modifies the selector 
(proactor).  When any of these happens, we physically or logically wake up 
the selector.


## History

`asyncslot` is derived from
[qasync](https://github.com/CabbageDevelopment/qasync) but rewritten from 
scratch.  qasync is a fork of 
[asyncqt](https://github.com/gmarull/asyncqt), which is a fork of
[quamash](https://github.com/harvimt/quamash).


## License

BSD License.

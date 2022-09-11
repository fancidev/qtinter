# asyncslot

[![build](https://github.com/fancidev/asyncslot/actions/workflows/build.yml/badge.svg)](https://github.com/fancidev/asyncslot/actions/workflows/build.yml)
[![tests](https://github.com/fancidev/asyncslot/actions/workflows/tests.yml/badge.svg)](https://github.com/fancidev/asyncslot/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/fancidev/asyncslot/branch/master/graph/badge.svg?token=JZ5ON6CHKA)](https://codecov.io/gh/fancidev/asyncslot)
[![PyPI](https://img.shields.io/pypi/v/asyncslot)](https://pypi.org/project/asyncslot/)

`asyncslot` is a Python module that allows you to use asyncio-based 
libraries in Python for Qt.

## Synopsis

To use asyncio-based libraries in Python for Qt, wrap `app.exec()` inside 
`AsyncSlotRunner`, and connect signal to a coroutine function using 
`asyncSlot`.

A minimal working GUI example (taken from `examples/minimal_gui.py`):

```Python
import asyncio
from PySide6 import QtWidgets
from asyncslot import asyncSlot, AsyncSlotRunner

async def say_hi():
    await asyncio.sleep(1)
    QtWidgets.QMessageBox.information(None, "Demo", "Hi")

app = QtWidgets.QApplication()
button = QtWidgets.QPushButton()
button.setText('Say Hi after one second')
button.clicked.connect(asyncSlot(say_hi))  # <-- instead of connect(say_hi)
button.show()

with AsyncSlotRunner():  # <-- wrap in Runner
    app.exec()
```

## Requirements

`asyncslot` supports the following:

- Python version: 3.7 or higher
- Qt binding: PyQt5, PyQt6, PySide2, PySide6
- Operating system: Linux, MacOS, Windows


## Installation

```commandline
pip install asyncslot
```

The above does _not_ install the Qt bindings.  To install Qt bindings, you may

```commandline
pip install PyQt6
```

Alternatively, you may install `asyncslot` together with your Qt binding of 
choice, for example

```commandline
pip install asyncslot[PyQt6]
```


## Details

`asyncslot` embeds a logical asyncio event loop (`AsyncSlotEventLoop`) 
within a physical Qt event loop (`QEventLoop`), so that Python libraries 
written for asyncio can be used by a Python for Qt application.

### Running Modes

An `AsyncSlotEventLoop` may be run in _attached mode_ or _nested mode_.

Use `AsyncSlotEventLoop` as a context manager to run it in attached mode.  
This mode only installs the logical asyncio event loop; the physical Qt 
event loop must still be run as usual, e.g. by `app.exec()`.  This is the 
preferred workflow as it integrates seamlessly with an existing Qt app.

Call `AsyncSlotEventLoop.run_forever` to run it in nested mode.  This starts 
a (possibly nested) Qt event loop using `QEventLoop.exec()` and waits until 
it exits.  This is the standard asyncio workflow and is convenient for 
unit testing, but it is not recommended for integration with an existing Qt 
app as nested event loops are advised against by Qt.

For either mode, a (global) `QCoreApplication` (or `QApplication` /
`QGuiApplication`) instance must exist before running any coroutine,
as is required by Qt.

### Clean-up

To properly release the resources of the event loop after it stops, you 
should call `shutdown_asyncgens` and `shutdown_default_executor`, followed
by `close`.  The first two methods are actually coroutines and therefore
must be run from within the event loop.

For attached mode, use the `asyncslot.AsyncSlotRunner` context manager, 
which handles clean-up automatically.  Note, however, that it actually runs 
the first two coroutines in nested mode, i.e. a Qt event loop is started.  
Your code should be prepared for this.

For nested mode, `asyncio.run()` handles clean-up automatically.


### The `asyncSlot` Adaptor

`asyncslot.asyncSlot` wraps a coroutine function (one defined by `async def`)
to make it usable as a Qt slot.  Without wrapping, a coroutine function
(whether decorated with `QtCore.Slot`/`PyQt6.pyqtSlot` or not)
generally cannot be used as a slot because calling it merely returns a 
coroutine object instead of performing real work.

Under the hood, `asyncslot.asyncSlot` calls `AsyncSlotEventLoop.run_task`,
a custom method which creates a Task wrapping the coroutine and executes
it immediately until the first suspension point.

This is designed to work with a common pattern where some work has to be
performed immediately in response to a signal.  For example, the `clicked`
handler of a "Send Order" button normally disables the button on entry
before actually sending the order over network, to avoid sending duplicate
orders.  For this to work correctly, the code until the first suspension 
point must be executed synchronously.

An `AsyncSlotEventLoop` must be running when a coroutine wrapped by 
`asyncSlot` is called, or a `RuntimeError` will be raised.

It is not recommended to decorate a coroutine function with `asyncSlot`
as that would make an `async def` function into a normal function, which
is confusing.


### Cancellation

To cancel a running coroutine from within itself, raise 
`asyncio.CancelledError`.

To retrieve the `Task` object from within the running coroutine and store
it somewhere to be used later, call `asyncio.current_task()` from within
the running coroutine.


## Implementation Notes

By embedding a (logical) asyncio event loop inside a (physical) Qt event 
loop, what's not changed (from the perspective of the asyncio event loop) is 
that all calls (other than `call_soon_threadsafe`) are still made from the 
same thread.  This frees us from multi-threading complexities.

What has changed, however, is that in a standalone asyncio event loop, no 
code can run when the scheduler (specifically, `_run_once`) is blocked in 
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
and before `_run_once` is called again as _injected code_.  We must 
examine and handle the implications of such code.

We do this by fitting injected code execution into the standalone asyncio
event loop model.  Specifically, we treat injected code as if they were 
scheduled with `call_soon_threadsafe`, which wakes up the selector and
executes the code.  _With_ some loss of generality, we assume no IO event
nor timed callback is ready at the exact same time, so that the scheduler 
will be put back into blocking `select` immediately after the code finishes 
running (unless the code calls `stop`).  This simplification is acceptable
because the precise timing of multiple IO or timer events should not be 
relied upon.

In practice, we cannot actually wake up the asyncio scheduler every time 
injected code is executed, firstly because there's no way to detect their
execution and secondly because doing so would be highly inefficient.
Instead, we _assume_ that injected code which does not access the event loop
object or its selector is benign enough to be treated as _independent_
from the asyncio event loop ecosystem and may be safely ignored.

This leaves us to just consider injected code that accesses the event loop 
object or its selector and examine its impact on scheduling.  The scheduler
depends on three things:  the `_ready` queue for "soon" callbacks, the 
`_scheduled` queue for timer callbacks, and `_selector` for IO events.
If the injected code touches any of these things, it needs to be handled.

While the public interface of `AbstractEventLoop` has numerous methods, the 
methods that modify those three things boil down to `call_soon`, `call_at`, 
`call_later`, (arguably) `stop`, and anything that modifies the selector 
(proactor).  When any of these happens, we physically or logically wake up 
the selector to simulate a `call_soon_threadsafe` call.


## History

`asyncslot` is derived from
[qasync](https://github.com/CabbageDevelopment/qasync) but rewritten from 
scratch.  qasync is a fork of 
[asyncqt](https://github.com/gmarull/asyncqt), which is a fork of
[quamash](https://github.com/harvimt/quamash).


## License

BSD License.

""" _base_events.py - event loop implementation using Qt """

import asyncio
import enum
import signal
import sys
import threading
import traceback
from asyncio import events
from typing import Optional
from ._selectable import *


__all__ = 'QiBaseEventLoop', 'QiLoopMode',


class _QiYield(Exception):
    """ Raised by a _QiSelectable to indicate that no IO is readily
    available and that _run_once should yield to the Qt event loop. """
    pass


class _InterruptEvent:
    __slots__ = '_flag',

    def __init__(self):
        self._flag = False

    def set(self) -> None:
        self._flag = True

    def is_set(self) -> bool:
        return self._flag

    def clear(self) -> None:
        self._flag = False


def _interrupt_handler(sig, frame):
    assert sig == signal.SIGINT
    # if frame is not None:
    #     print(frame.f_locals)
    if frame is not None and '_interrupt_event' in frame.f_locals:
        _interrupt_event = frame.f_locals['_interrupt_event']
        if isinstance(_interrupt_event, _InterruptEvent):
            _interrupt_event.set()
            return
    return signal.default_int_handler(sig, frame)


class _QiNotifierImpl(_QiNotifier):

    def __init__(self, loop: "QiBaseEventLoop", qi_object):
        # The following creates a reference cycle.  Call close() to
        # break the cycle.
        self._loop = loop

        # Register callback.
        self._qi_object = qi_object
        self._qi_object.add_callback(self._on_notified)

        # Install a SIGINT handler if no custom handler is installed.
        self._interrupt_handler_installed = False
        if signal.getsignal(signal.SIGINT) is signal.default_int_handler:
            try:
                signal.signal(signal.SIGINT, _interrupt_handler)
            except (ValueError, OSError):
                pass
            else:
                self._interrupt_handler_installed = True

    def _on_notified(self, _interrupt_event=_InterruptEvent()):
        # If Ctrl+C is pressed while the loop is in a 'non-blocking'
        # select(), the select() will be woken up (due to set_wakeup_fd)
        # and the _notified signal emitted.  KeyboardInterrupt will be
        # raised at the first point where Python byte code is run, i.e.
        # this method.  We wrap the body in try-except to handle this.
        try:
            if _interrupt_event.is_set():
                raise KeyboardInterrupt
            if self._loop is not None:
                self._loop._qi_loop_iteration()
            else:
                # TODO: print a warning that notification is received after
                # TODO: the notifier is closed.
                pass
        except KeyboardInterrupt as exc:
            # We catch Ctrl+C only once.  If Ctrl+C is pressed again
            # immediately, the program will crash.
            if self._loop is not None:
                self._loop._qi_loop_interrupt(exc)
            else:
                pass  # ignore Ctrl+C for once
        finally:
            _interrupt_event.clear()

    def no_result(self):
        raise _QiYield

    def notify(self):
        self._qi_object.invoke_callbacks()

    def wakeup(self):
        self._loop._write_to_self()

    def close(self):
        if self._loop is not None:
            self._qi_object.remove_callback(self._on_notified)
            self._qi_object = None
            self._loop = None
        if self._interrupt_handler_installed:
            try:
                if signal.getsignal(signal.SIGINT) is _interrupt_handler:
                    signal.signal(signal.SIGINT, signal.default_int_handler)
            except (ValueError, OSError):
                pass
            finally:
                self._interrupt_handler_installed = False


def _create_notifier(loop: "QiBaseEventLoop"):
    from .bindings import _QiObjectImpl
    return _QiNotifierImpl(loop, _QiObjectImpl())


class QiLoopMode(enum.Enum):
    OWNER = 'OWNER'
    GUEST = 'GUEST'
    NATIVE = 'NATIVE'


class _QiDeferred(SystemExit):
    """Special exception used by QiBaseEventLoop.run_modal() to break out
    of _run_once and execute a callback."""
    def __init__(self, callback):
        super().__init__()
        self.__callback = callback

    def execute(self):
        self.__callback()


class QiBaseEventLoop(asyncio.BaseEventLoop):
    """Implements the scheduling logic of qtinter event loop.

    An asyncio event loop can be in one of the following 'states':
      - STOPPED: loop is not polling for IO or processing events
      - RUNNING: loop is polling for IO or processing events
      - CLOSED: loop is closed and cannot be used in any way

    The _closed and _thread_id attributes determine the current state:

                 _closed    _thread_id
      RUNNING    False      not None
      STOPPED    False      None
      CLOSED     True       None

    A QiBaseEventLoop can operate in one of the following 'modes':
      - OWNER: run_forever creates a QEventLoop and calls exec() on it
      - GUEST: user is responsible for creating and running a Qt event loop
      - NATIVE: run_forever creates a native asyncio event loop free of Qt

    The __qt_event_loop and __notifier attributes are set as follows
    depending on the operating mode (provided the loop is RUNNING):

                __qt_event_loop    __notifier
      OWNER     not None           not None
      GUEST     None               not None
      NATIVE    None               None

    A RUNNING QiBaseEventLoop in OWNER or GUEST mode can
    further be in one of two sub-states: PROCESSING or SELECTING.

      - PROCESSING: _qi_loop_iteration() is being executed
      - SELECTING: _qi_loop_iteration() is waiting to be scheduled

    A RUNNING QiBaseEventLoop in NATIVE mode is always PROCESSING.

    The __processing attribute determines the current sub-state (provided
    the loop is RUNNING).

    OWNER Mode
    ----------

    A loop operating in OWNER mode launches a QEventLoop and calls
    exec() on it when run_forever() is called.  If no QObjects are accessed,
    such a loop provides 100% API and semantics compatibility with asyncio.
    This mode is useful for accessing Qt objects from asyncio-driven code.

    GUEST Mode
    ----------

    A loop operating in GUEST mode never launches a Qt event loop
    itself.  The normal workflow is for the user to call start() first and
    then launch a Qt event loop, e.g. by calling one of QEventLoop.exec(),
    QCoreApplication.exec(), QThread.exec(), etc.  After the Qt event loop
    exits, the user should call stop().

    Note that start() and stop() only change the (logical) state of the
    QiBaseEventLoop; they have no effect on the (physical) Qt event loop
    and is in fact independent of the lifetime of the latter.

    NATIVE Mode
    -----------

    If run_forever() is called on a loop operating in NATIVE mode,
    a native asyncio event loop is run, which blocks the calling thread
    until stop() is called.  This is designed for running clean-up code
    after the Qt event loop has exited.  Such clean-up code should finish
    as soon as possible, and should not access any Qt object since no Qt
    event loop is running.
    """
    def __init__(self, *args, **kwargs):
        # The operating mode.  This can only be changed when the loop is
        # not running.  As a sanity check, the _stopping flag must be
        # False when changing the mode.
        # self.__standalone = True
        self.__mode = QiLoopMode.OWNER

        # If self is created in STANDALONE mode and is running,
        # __qt_event_loop is set to the QEventLoop that is being run.
        # In any other case, __qt_event_loop is set to None.
        self.__qt_event_loop = None

        # If self is running in STANDALONE or INTEGRATED mode, __notifier
        # is set to a notifier object and is attached to the selector to
        # notify us when IO is available or timeout occurs.  In any other
        # case, __notifier is set to None.
        self.__notifier: Optional[_QiNotifier] = None

        # __processing is set to True in _qi_loop_iteration to
        # indicate that a 'normal' asyncio event processing iteration
        # (i.e. _run_once) is running.  It is also set to True when the
        # loop is running in EXCLUSIVE mode.
        self.__processing = False

        # Any exception raised by self._process_asyncio_events is stored
        # in __run_once_error to be propagated later to the caller of
        # self.run_forever, as QEventLoop.exec() does not propagate
        # exceptions.  Exceptions raised by tasks are normally not
        # propagated except for SystemExit and KeyboardInterrupt.
        self.__run_once_error: Optional[BaseException] = None

        # When the loop is running in INTEGRATED or STANDALONE mode,
        # __old_agen_hook is set to the asyncgen hooks before the loop is
        # started, so that they can be restored after the loop is stopped.
        self.__old_agen_hooks: Optional[tuple] = None

        # If __call_soon_eagerly is True, _call_soon does not schedule the
        # callback but instead invoke it immediately.  This flag is used by
        # run_task to eagerly execute the first step of a task.
        self.__call_soon_eagerly = False

        # Remaining number of 'ready' callbacks to invoke from the
        # last call to _run_once().  This may be greater than zero
        # if a callback raised SystemExit or KeyboardInterrupt.
        # Used to resume _run_once() without polling.
        self.__ntodo = 0

        # Need to invoke base constructor after initializing member variables
        # for compatibility with Python 3.7's BaseProactorEventLoop (Windows),
        # which calls self.call_soon() indirectly from its constructor.
        super().__init__(*args, **kwargs)  # noqa

    # =========================================================================
    # Custom methods
    # =========================================================================

    def set_mode(self, mode: QiLoopMode) -> None:
        self._check_closed()
        self._check_running()
        if self._stopping:
            raise RuntimeError('cannot call set_mode when the loop is stopping')
        self.__mode = mode

    def run_task(self, coro, *, name=None):
        try:
            self.__call_soon_eagerly = True
            if name is None:
                return self.create_task(coro)
            else:
                return self.create_task(coro, name=name)
        finally:
            # This flag is normally reset by _call_soon, but also reset here
            # in case _call_soon is not called due to exception.
            self.__call_soon_eagerly = False

    def exec_interleaved(self, callback) -> None:
        """Schedule callback to be executed immediately after the current
        loop iteration as if it were interleaved code.  This method must
        be called from a callback or coroutine.

        If this function is called more than once, the callbacks will be
        scheduled in reverse (i.e. LIFO) order.  Note that only the
        first-to-run callback is executed immediately after the current
        loop iteration; the remaining callbacks may be interleaved with
        other (truly) interleaved code.
        """
        def fn():
            raise _QiDeferred(callback)
        self.call_next(fn)

    def start(self) -> None:
        if self.__mode != QiLoopMode.GUEST:
            raise RuntimeError('QiBaseEventLoop.start() can only be '
                               'called for a loop operating in GUEST mode')
        self._qi_loop_startup()

    def _qi_loop_startup(self) -> None:
        """ Start the logical asyncio event loop. """

        # ---- BEGIN COPIED FROM BaseEventLoop.run_forever
        self._check_closed()
        self._check_running()
        self._set_coroutine_origin_tracking(self._debug)
        self._thread_id = threading.get_ident()

        old_agen_hooks = sys.get_asyncgen_hooks()
        sys.set_asyncgen_hooks(firstiter=self._asyncgen_firstiter_hook,
                               finalizer=self._asyncgen_finalizer_hook)
        # ---- END COPIED FROM BaseEventLoop.run_forever

        self.__old_agen_hooks = old_agen_hooks

        self.__notifier = _create_notifier(self)
        self.__notifier.notify()  # schedule initial _run_once

        # Do not set notifier if a TestSelector is used (during testing).
        if hasattr(self._selector, 'set_notifier'):
            self._selector.set_notifier(self.__notifier)  # noqa

        events._set_running_loop(self)  # TODO: what does this do?

    def _qi_loop_cleanup(self) -> None:
        """ Stop the logical asyncio event loop. """
        if self.__old_agen_hooks is not None:
            old_agen_hooks = self.__old_agen_hooks
            self.__old_agen_hooks = None
        else:
            old_agen_hooks = sys.get_asyncgen_hooks()
        if self.__notifier is not None:
            # Do not set notifier if a TestSelector is used (during testing).
            if hasattr(self._selector, 'set_notifier'):
                self._selector.set_notifier(None)  # noqa
            self.__notifier.close()
            self.__notifier = None
        # ---- BEGIN COPIED FROM BaseEventLoop.run_forever
        self._stopping = False
        self._thread_id = None
        events._set_running_loop(None)
        self._set_coroutine_origin_tracking(False)
        sys.set_asyncgen_hooks(*old_agen_hooks)
        # ---- END COPIED FROM BaseEventLoop.run_forever

    def _qi_loop_iteration(self):
        """ This slot is connected to the notified signal of self.__notifier,
        which is emitted whenever asyncio events are possibly available
        and need to be processed."""
        assert not self.is_closed(), 'loop unexpectedly closed'
        assert self.is_running(), 'loop unexpectedly stopped'

        # Process ready callbacks, ready IO, and scheduled callbacks that
        # have passed the schedule time.  Run only once to avoid starving
        # the Qt event loop.
        try:
            self.__processing = True
            try:
                self._run_once()
            finally:
                self.__processing = False
        except _QiYield:
            # Ignore _stopping flag until select() returns.  This follows
            # asyncio behavior.
            # TODO: but this should not happen, because 0 timeout is passed
            # TODO: to select() if _stopping is True.
            pass
        except _QiDeferred as deferred:
            # The current loop iteration was interrupted in order to execute
            # some callback as if it were interleaved code.  This is used to
            # execute a Qt function that launches a nested Qt event loop.
            # TODO: check if we can stop a Qt loop when there are nested
            # TODO: loop running.
            # Schedule the next loop iteration so that we can pick up where
            # we left off.
            self.__notifier.notify()
            deferred.execute()
        except BaseException as exc:
            self._qi_loop_interrupt(exc)
        else:
            # To be consistent with asyncio behavior, check the _stopping
            # flag only after running a full iteration of _run_once.
            if self._stopping:
                if self.__qt_event_loop is not None:
                    # In OWNER mode, quit the loop and let run_forever
                    # perform clean up.
                    self.__qt_event_loop.exit(0)
                else:
                    # In GUEST mode, stop immediately because there is
                    # no 'caller' to perform the cleanup for us.
                    self._qi_loop_cleanup()
            else:
                # Schedule next iteration if this iteration did not block
                self.__notifier.notify()

    def _qi_loop_interrupt(self, exc: BaseException):
        """Terminate the loop abnormally with the given exception.

        This method is called by:

          (1) QiBaseEventLoop._qi_loop_iteration() if
              _run_once raised a BaseException, typically SystemExit
              or KeyboardInterrupt; and

          (2) _QiNotifier._on_notified() if KeyboardInterrupt
              is raised during processing the notification.

        """
        if self.__qt_event_loop is not None:
            # In OWNER mode, propagate the exception to the caller
            # of run_forever.
            self.__run_once_error = exc
            self.__qt_event_loop.exit(1)
        else:
            # In GUEST mode, stop the loop immediately and raise
            # the error into the Qt event loop.  For PyQt this will
            # terminate the process; for PySide this will log an error
            # and then ignored.
            # TODO: if KeyboardInterrupt is raised, the object may not
            # TODO: be in a consistent state to perform cleanup.
            self._qi_loop_cleanup()
            raise exc
            # TODO: implement consistent behavior under both bindings.
            # TODO: maybe call some exception handler and let it decide
            # TODO: what to do?

    # =========================================================================
    # Compatibility with Python 3.7
    # =========================================================================

    if sys.version_info < (3, 7):
        raise RuntimeError('qtinter requires Python 3.7 or higher')

    elif sys.version_info < (3, 8):
        _check_running = asyncio.BaseEventLoop._check_runnung

    # =========================================================================
    # Methods defined in asyncio.AbstractEventLoop
    # =========================================================================

    # -------------------------------------------------------------------------
    # Running and stopping the event loop.
    # -------------------------------------------------------------------------

    def run_forever(self) -> None:
        """ Run the event loop until stop() is called. """

        if self.__mode == QiLoopMode.GUEST:
            raise RuntimeError('run_forever cannot be called for a loop '
                               'operating in GUEST mode')

        if self.__mode == QiLoopMode.NATIVE:
            try:
                self.__processing = True
                return super().run_forever()
            finally:
                self.__processing = False

        assert self.__mode == QiLoopMode.OWNER

        from .bindings import QtCore
        if QtCore.QCoreApplication.instance() is None:
            # TODO: do we need the same check in start()?
            raise RuntimeError('An instance of QCoreApplication or its '
                               'derived class must be created in order '
                               'to run QiBaseEventLoop')

        try:
            self._qi_loop_startup()
            self.__qt_event_loop = QtCore.QEventLoop()
            if hasattr(QtCore.QEventLoop, 'exec'):
                exit_code = self.__qt_event_loop.exec()
            else:
                exit_code = self.__qt_event_loop.exec_()
            if exit_code != 0:
                # Propagate exception from _qi_loop_iteration() if
                # one is set.  The exception is not set if the Qt loop
                # is terminated by e.g. QCoreApplication.exit().  Note
                # also that if QCoreApplication.exit() has been called
                # before calling run_forever, QEventLoop.exec() would
                # return immediately.
                if self.__run_once_error is not None:
                    raise self.__run_once_error  # TODO: test this
                else:
                    raise RuntimeError(
                        f"Qt event loop exited with code '{exit_code}'")
        except BaseException:
            # TODO: improve diagnosis
            print(traceback.format_exc(), file=sys.stderr)
            raise
        finally:
            self.__run_once_error = None
            self.__qt_event_loop = None
            self._qi_loop_cleanup()

    # run_until_complete = BaseEventLoop.run_until_complete

    def stop(self) -> None:
        """ Request the loop to stop.

        The precise semantics are as follows:

        If the loop is operating in OWNER mode:

          - If stop() is called when the loop is STOPPED, the next time the
            loop is RUNNING it will run exactly one iteration and then stop.

          - If stop() is called from a callback of a RUNNING loop, the loop
            will stop after completing the current iteration.

          - If stop() is called from interleaved code (a Qt slot) when the
            loop is RUNNING, treat as if called via call_soon_threadsafe():
            wake up the selector, which will run one iteration and stop.

        If the loop is operating in GUEST mode:

          - If stop() is called when the loop is STOPPED, raise an error.
            (The pre-stop idiom is not supported.)

          - If stop() is called from a callback of a RUNNING loop, either
            in INTEGRATED or EXCLUSIVE mode, the loop will stop after
            completing the current iteration.

          - If stop() is called from interleaving code (a Qt slot) when
            the loop is RUNNING in INTEGRATED mode, wake up the selector
            and stop the loop immediately, since there might not be a Qt
            loop to execute the next iteration.

        If the loop is operating in NATIVE mode:

          - If stop() is called when the loop is STOPPED, the next time the
            loop is RUNNING it will run exactly one iteration and then stop.

          - If stop() is called from a callback of a RUNNING loop, the loop
            will stop after completing the current iteration.

        In any case, if KeyboardInterrupt or SystemExit is raised when
        processing an iteration, that iteration is interrupted, the loop
        is stopped immediately, and the exception is propagated to the
        caller of run_forever if operating in OWNER or NATIVE mode or
        thrown into the Qt loop if operating in GUEST mode.
        """
        if self.__mode == QiLoopMode.NATIVE:
            super().stop()

        elif self.__mode == QiLoopMode.OWNER:
            if self.is_running() and not self.__processing:
                self._write_to_self()
            super().stop()

        else:
            assert self.__mode == QiLoopMode.GUEST
            if not self.is_running():
                raise RuntimeError('QiBaseEventLoop: stop can only be called '
                                   'when a loop operating in GUEST mode is '
                                   'running')
            elif self.__processing:
                super().stop()
            else:
                self._write_to_self()
                super().stop()  # this only sets the flat
                self._qi_loop_cleanup()

    # is_running = BaseEventLoop.is_running
    # is_closed = BaseEventLoop.is_closed
    # close = BaseEventLoop.close
    # shutdown_asyncgens = BaseEventLoop.shutdown_asyncgens
    # shutdown_default_executor = BaseEventLoop.shutdown_default_executor

    # -------------------------------------------------------------------------
    # Methods scheduling callbacks.  All these return Handles.
    # -------------------------------------------------------------------------

    # _timer_handle_cancelled: see BaseEventLoop

    def call_soon(self, *args, **kwargs):
        # If called from interleaving code when the loop is SELECTING,
        # treat as if called by call_soon_threadsafe().
        if self.is_running() and not self.__processing:
            self._write_to_self()

        # Eager execution if called from run_task().
        handle = super().call_soon(*args, **kwargs)
        if self.__call_soon_eagerly:
            self.__call_soon_eagerly = False
            # asyncio does not support recursive task execution, so 'suspend'
            # the current task before running the child task and 'resume' it
            # after the child task completes one step.
            current_task = asyncio.tasks.current_task(self)
            if current_task is not None:
                asyncio.tasks._leave_task(self, current_task)
            try:
                # only propagates SystemExit and KeyboardInterrupt
                handle._run()
            finally:
                # Cancel the handle because it is already in the _ready queue
                handle.cancel()
                # Resume the parent task if any.
                if current_task is not None:
                    asyncio.tasks._enter_task(self, current_task)
        return handle

    def call_later(self, *args, **kwargs):
        if self.is_running() and not self.__processing:
            self._write_to_self()
        return super().call_later(*args, **kwargs)

    def call_at(self, *args, **kwargs):
        if self.is_running() and not self.__processing:
            self._write_to_self()
        return super().call_at(*args, **kwargs)

    # time: see BaseEventLoop
    # create_future: see BaseEventLoop

    # This is a custom method!
    def call_next(self, callback, *args, context=None):
        """Schedule callback to be called right after the current callback.
        Must be called from within a callback (i.e. not from another thread
        or from interleaved code).

        Unless the current callback raises KeyboardInterrupt or SystemExit,
        callback is guaranteed to be called immediately afterwards (in the
        same loop iteration).
        """
        if not self.__processing:
            raise RuntimeError('QiBaseEventLoop.call_next() must be called '
                               'from a coroutine or callback')

        handle = super().call_soon(callback, *args, context=context)
        assert self._ready.pop() is handle
        self._ready.appendleft(handle)
        self.__ntodo += 1
        return handle

    def _run_once(self):
        """Override asyncio.BaseEventLoop._run_once to support pause
        and resume in _ready queue processing.  This is used to support
        nested Qt event loop.

        Most part of the code is copied verbatim.
        """
        from asyncio.base_events import (
            heapq,
            _MIN_SCHEDULED_TIMER_HANDLES,
            _MIN_CANCELLED_TIMER_HANDLES_FRACTION,
            MAXIMUM_SELECT_TIMEOUT,
            logger,
            _format_handle,
        )

        # --- BEGIN COPIED FROM asyncio.BaseEventLoop._run_once

        sched_count = len(self._scheduled)
        if (sched_count > _MIN_SCHEDULED_TIMER_HANDLES and
            self._timer_cancelled_count / sched_count >
                _MIN_CANCELLED_TIMER_HANDLES_FRACTION):
            # Remove delayed calls that were cancelled if their number
            # is too high
            new_scheduled = []
            for handle in self._scheduled:
                if handle._cancelled:
                    handle._scheduled = False
                else:
                    new_scheduled.append(handle)

            heapq.heapify(new_scheduled)
            self._scheduled = new_scheduled
            self._timer_cancelled_count = 0
        else:
            # Remove delayed calls that were cancelled from head of queue.
            while self._scheduled and self._scheduled[0]._cancelled:
                self._timer_cancelled_count -= 1
                handle = heapq.heappop(self._scheduled)
                handle._scheduled = False

        timeout = None
        if self._ready or self._stopping:
            timeout = 0
        elif self._scheduled:
            # Compute the desired timeout.
            when = self._scheduled[0]._when
            timeout = min(max(0, when - self.time()), MAXIMUM_SELECT_TIMEOUT)

        # >>> CHANGED: Do not select if last _run_once has pending items
        # >>> Python 3.7 does logging for select() call; Python 3.8 and
        # >>> above don't.
        if self.__ntodo == 0:
            if sys.version_info < (3, 8) and self._debug and timeout != 0:
                import logging  # <<< PATCH
                t0 = self.time()
                event_list = self._selector.select(timeout)
                dt = self.time() - t0
                if dt >= 1.0:
                    level = logging.INFO
                else:
                    level = logging.DEBUG
                nevent = len(event_list)
                if timeout is None:
                    logger.log(level, 'poll took %.3f ms: %s events',
                               dt * 1e3, nevent)
                elif nevent:
                    logger.log(level,
                               'poll %.3f ms took %.3f ms: %s events',
                               timeout * 1e3, dt * 1e3, nevent)
                elif dt >= 1.0:
                    logger.log(level,
                               'poll %.3f ms took %.3f ms: timeout',
                               timeout * 1e3, dt * 1e3)
            else:
                event_list = self._selector.select(timeout)
            self._process_events(event_list)
        # >>> END OF CHANGED

        # Handle 'later' callbacks that are ready.
        end_time = self.time() + self._clock_resolution
        while self._scheduled:
            handle = self._scheduled[0]
            if handle._when >= end_time:
                break
            handle = heapq.heappop(self._scheduled)
            handle._scheduled = False
            self._ready.append(handle)

        # This is the only place where callbacks are actually *called*.
        # All other places just add them to ready.
        # Note: We run all currently scheduled callbacks, but not any
        # callbacks scheduled by callbacks run this time around --
        # they will be run the next time (after another I/O poll).
        # Use an idiom that is thread-safe without using locks.

        # >>> CHANGED: Use ntodo from last _run_once if any callback left
        if self.__ntodo == 0:
            self.__ntodo = len(self._ready)

        while self.__ntodo > 0:
            self.__ntodo -= 1
        # >>> END OF CHANGE

            handle = self._ready.popleft()
            if handle._cancelled:
                continue
            if self._debug:
                try:
                    self._current_handle = handle
                    t0 = self.time()
                    handle._run()
                    dt = self.time() - t0
                    if dt >= self.slow_callback_duration:
                        logger.warning('Executing %s took %.3f seconds',
                                       _format_handle(handle), dt)
                finally:
                    self._current_handle = None
            else:
                handle._run()
        handle = None  # Needed to break cycles when an exception occurs.

        # --- END COPIED FROM asyncio.BaseEventLoop._run_once

    # -------------------------------------------------------------------------
    # Method scheduling a coroutine object: create a task.
    # -------------------------------------------------------------------------

    # create_task = BaseEventLoop.create_task

    # -------------------------------------------------------------------------
    # Methods for interacting with threads.
    # -------------------------------------------------------------------------

    # call_soon_threadsafe: BaseEventLoop
    # run_in_executor: BaseEventLoop
    # set_default_executor: BaseEventLoop

    # -------------------------------------------------------------------------
    # Network I/O methods returning Futures.
    # -------------------------------------------------------------------------

    # getaddrinfo = BaseEventLoop.getaddrinfo
    # getnameinfo = BaseEventLoop.getnameinfo
    # create_connection = BaseEventLoop.create_connection
    # create_server = BaseEventLoop.create_server
    # sendfile = BaseEventLoop.sendfile
    # start_tls = BaseEventLoop.start_tls
    # create_unix_connection = _UnixSelectorEventLoop.create_unix_connection
    # create_unix_server = _UnixSelectorEventLoop.create_unix_server
    # create_datagram_endpoint = BaseEventLoop.create_datagram_endpoint

    # -------------------------------------------------------------------------
    # Pipes and subprocesses.
    # -------------------------------------------------------------------------

    # connect_read_pipe = BaseEventLoop.connect_read_pipe
    # connect_write_pipe = BaseEventLoop.connect_write_pipe
    # subprocess_shell = BaseEventLoop.subprocess_shell
    # subprocess_exec = BaseEventLoop.subprocess_exec

    # -------------------------------------------------------------------------
    # Ready-based callback registration methods.
    # -------------------------------------------------------------------------

    # add_reader = BaseSelectorEventLoop.add_reader
    # remove_reader = BaseSelectorEventLoop.remove_reader
    # add_writer = BaseSelectorEventLoop.add_writer
    # remove_writer = BaseSelectorEventLoop.remove_writer

    # -------------------------------------------------------------------------
    # Completion based I/O methods returning Futures.
    # -------------------------------------------------------------------------

    # sock_recv = BaseSelectorEventLoop.sock_recv
    # sock_recv_into = BaseSelectorEventLoop.sock_recv_into
    # sock_sendall = BaseSelectorEventLoop.sock_sendall
    # sock_connect = BaseSelectorEventLoop.sock_connect
    # sock_accept = BaseSelectorEventLoop.sock_accept
    # sock_sendfile = BaseSelectorEventLoop.sock_sendfile

    # -------------------------------------------------------------------------
    # Signal handling.
    # -------------------------------------------------------------------------

    # add_signal_handler = _UnixSelectorEventLoop.add_signal_handler
    # remove_signal_handler = _UnixSelectorEventLoop.remove_signal_handler

    # -------------------------------------------------------------------------
    # Task factory.
    # -------------------------------------------------------------------------

    # set_task_factory = BaseEventLoop.set_task_factory
    # get_task_factory = BaseEventLoop.get_task_factory

    # -------------------------------------------------------------------------
    # Error handlers.
    # -------------------------------------------------------------------------

    # get_exception_handler = BaseEventLoop.get_exception_handler
    # set_exception_handler = BaseEventLoop.set_exception_handler
    # default_exception_handler = BaseEventLoop.default_exception_handler
    # call_exception_handler = BaseEventLoop.call_exception_handler

    # -------------------------------------------------------------------------
    # Debug flag management.
    # -------------------------------------------------------------------------

    # get_debug = BaseEventLoop.get_debug
    # set_debug = BaseEventLoop.set_debug

    # =========================================================================
    # Abstract methods defined by asyncio.BaseEventLoop
    # =========================================================================

    # _make_socket_transport = BaseSelectorEventLoop._make_socket_transport
    # _make_ssl_transport = BaseSelectorEventLoop._make_ssl_transport
    # _make_datagram_transport = BaseSelectorEventLoop._make_datagram_transport
    # _make_read_pipe_transport: see _UnixSelectorEventLoop
    # _make_write_pipe_transport: see _UnixSelectorEventLoop
    # _make_subprocess_transport: see _UnixSelectorEventLoop
    # _write_to_self: see BaseSelectorEventLoop / BaseProactorEventLoop
    # _process_events: see BaseSelectorEventLoop / BaseProactorEventLoop

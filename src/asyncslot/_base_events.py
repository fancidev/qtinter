""" _base_events.py - event loop implementation using Qt """

import asyncio
import functools
import selectors
import sys
import threading
import traceback
from asyncio import events
from typing import List, Optional, Tuple
from ._shim import QtCore


__all__ = ('AsyncSlotYield', 'AsyncSlotNotifier', 'AsyncSlotBaseEventLoop')


class AsyncSlotYield(Exception):
    """ Raised by an AsyncSlotSelectable to indicate that no IO is readily
    available and that _run_once should yield to the Qt event loop. """
    pass


class AsyncSlotNotifier(QtCore.QObject):
    notified = QtCore.Signal()

    def notify(self):
        self.notified.emit()


class AsyncSlotSelectable:  # protocol
    # A Selectable must support being called from interleaving code.

    def select(self, timeout: Optional[float] = None) \
            -> List[Tuple[selectors.SelectorKey, int]]:
        """
        If timeout <= 0 or some IO is ready, return whatever is ready
        immediately.  Otherwise, perform select with the given timeout in
        a separate thread and raise AsyncSlotYield.  When that select
        completes (either due to IO availability or timeout), call notify()
        on the notifier object set by a previous call to set_notifier().
        """
        raise NotImplementedError

    def set_notifier(self, notifier: Optional[AsyncSlotNotifier]) -> None:
        raise NotImplementedError


class AsyncSlotBaseEventLoop(asyncio.BaseEventLoop):
    def __init__(self, selector: AsyncSlotSelectable):

        # If self is running in blocking mode (using a nested QEventLoop),
        # __qt_event_loop is set to that QEventLoop.  If self is not running
        # or running in non-blocking mode, __qt_event_loop is set to None.
        self.__qt_event_loop: Optional[QtCore.QEventLoop] = None

        # When self is running, __notifier is attached to the selector to
        # receive notifications when IO is available or timeout occurs.
        # We connect to its notified signal to process asyncio events.
        self.__notifier: Optional[AsyncSlotNotifier] = None

        # True if the last call to _run_once raised AsyncSlotYield, which
        # means the embedded asyncio event loop is "logically" blocked in
        # select() waiting for IO or timeout.
        self.__blocked_in_select = False

        # Any exception raised by self._process_asyncio_events is stored
        # in __run_once_error to be propagated later to the caller of
        # self.run_forever, as QEventLoop.exec() does not propagate
        # exceptions.  Exceptions raised by tasks are normally not
        # propagated except for SystemExit and KeyboardInterrupt.
        self.__run_once_error: Optional[BaseException] = None

        self.__old_agen_hooks = None

        # If __call_soon_eagerly is True, _call_soon does not schedule the
        # callback but instead invoke it immediately.  This flag is used by
        # run_task to eagerly execute the first step of a task.
        self.__call_soon_eagerly = False

        # Need to invoke base constructor after initializing member variables
        # for compatibility with Python 3.7's BaseProactorEventLoop (Windows),
        # which calls self.call_soon() indirectly from its constructor.
        super().__init__(selector)  # noqa

    # =========================================================================
    # Custom method for AsyncSlot
    # =========================================================================

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

    def __enter__(self) -> None:
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

        # Must make queued connection to avoid calling the handler immediately
        self.__notifier = AsyncSlotNotifier()
        self.__notifier.notified.connect(functools.partial(
            self.__process_asyncio_events, notifier=self.__notifier),
            QtCore.Qt.ConnectionType.QueuedConnection)
        self.__notifier.notify()  # schedule initial _run_once

        self._selector.set_notifier(self.__notifier)  # noqa

        events._set_running_loop(self)  # TODO: what does this do?

    def __exit__(self, *args) -> None:
        """ Stop the logical asyncio event loop. """
        old_agen_hooks = self.__old_agen_hooks
        self.__old_agen_hooks = None
        if self.__notifier is not None:
            self._selector.set_notifier(None)  # noqa
            self.__notifier.notified.disconnect()
            self.__notifier = None
        # ---- BEGIN COPIED FROM BaseEventLoop.run_forever
        self._stopping = False
        self._thread_id = None
        events._set_running_loop(None)
        self._set_coroutine_origin_tracking(False)
        sys.set_asyncgen_hooks(*old_agen_hooks)
        # ---- END COPIED FROM BaseEventLoop.run_forever

    def __process_asyncio_events(self, *, notifier: AsyncSlotNotifier):
        """ This slot is connected to the notified signal of self.__notifier,
        which is emitted whenever asyncio events are possibly available
        and need to be processed."""
        if self.__notifier is not notifier:
            # Called from a queued signal handler for a stopped loop run
            # TODO: print a warning
            return

        assert not self.is_closed(), 'loop unexpectedly closed'
        assert self.is_running(), 'loop unexpectedly stopped'

        self.__blocked_in_select = False

        if self._stopping:
            if self.__qt_event_loop is not None:  # called from run_forever
                self.__qt_event_loop.exit(0)
            return

        # Process ready callbacks, ready IO, and scheduled callbacks that
        # have passed the schedule time.  Run only once to avoid starving
        # the Qt event loop.
        try:
            self._run_once()  # defined in asyncio.BaseEventLoop
        except AsyncSlotYield:
            self.__blocked_in_select = True
        except BaseException as exc:
            # TODO: call the exception handler if running in attached mode
            self.__run_once_error = exc
            if self.__qt_event_loop is not None:  # called from run_forever
                self.__qt_event_loop.exit(1)
            else:
                raise  # TODO: check what to do if called from run_task
        else:
            # Schedule next iteration if this iteration did not block
            self.__notifier.notify()

    # =========================================================================
    # Compatibility with Python 3.7
    # =========================================================================

    if sys.version_info < (3, 7):
        raise RuntimeError('asyncslot requires Python 3.7 or higher')

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
        if QtCore.QCoreApplication.instance() is None:
            raise RuntimeError('An instance of QCoreApplication or its '
                               'derived class must be create before running '
                               'AsyncSlotEventLoop')

        with self:
            try:
                self.__qt_event_loop = QtCore.QEventLoop()
                if hasattr(QtCore.QEventLoop, 'exec'):
                    exit_code = self.__qt_event_loop.exec()
                else:
                    exit_code = self.__qt_event_loop.exec_()
                if exit_code != 0:
                    # Propagate exception from _process_asyncio_events if
                    # one is set.  The exception is not set if the Qt loop
                    # is terminated by e.g. QCoreApplication.exit().
                    if self.__run_once_error is not None:
                        raise self.__run_once_error  # TODO: test this
                    else:
                        raise RuntimeError(
                            f"Qt event loop exited with code '{exit_code}'")
            except BaseException:
                print(traceback.format_exc(), file=sys.stderr)
                raise
            finally:
                self.__run_once_error = None
                self.__qt_event_loop = None

    # run_until_complete = BaseEventLoop.run_until_complete

    def stop(self) -> None:
        # A standalone asyncio event loop can never be stopped while it's
        # blocked in select(), because stop() must be called from the
        # event loop's thread.  But when embedded in a Qt event loop,
        # stop() may be called from a Qt slot when the asyncio loop is
        # blocked in select().  We treat this as if stop() was called
        # from call_soon_threadsafe().
        if self.__blocked_in_select:
            self._write_to_self()
        super().stop()

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
        if self.__blocked_in_select:
            self._write_to_self()
        # TODO: implement eager execution if called from run_task().
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
        if self.__blocked_in_select:
            self._write_to_self()
        return super().call_later(*args, **kwargs)

    def call_at(self, *args, **kwargs):
        if self.__blocked_in_select:
            self._write_to_self()
        return super().call_at(*args, **kwargs)

    # time: see BaseEventLoop
    # create_future: see BaseEventLoop

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

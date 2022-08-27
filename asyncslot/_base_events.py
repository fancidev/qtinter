""" _base_events.py - event loop implementation using Qt """

import asyncio
import sys
import threading
from asyncio import events
from typing import Optional

from PySide6 import QtCore


class AsyncSlotYield(Exception):
    """ Raised by a custom AsyncSlot selector to indicate that no IO
    is immediately available and that _run_once should yield to the Qt
    event loop. """
    pass


class _AsyncSlotEventNotifier(QtCore.QObject):
    asyncioEventAvailable = QtCore.Signal(int)


class AsyncSlotBaseEventLoop(asyncio.BaseEventLoop):
    def __init__(self):
        super().__init__()

        # If self is running in blocking mode (using a nested QEventLoop),
        # _qt_event_loop is set to that QEventLoop.  If self is not running
        # or running in non-blocking (guest) mode, _qt_event_loop is set
        # to None.
        self._qt_event_loop: Optional[QtCore.QEventLoop] = None

        # If self is running, _event_notifier is set to a QObject whose
        # sole use is to emit a signal for self to process asyncio events.
        self._event_notifier: Optional[_AsyncSlotEventNotifier] = None

        # A counter that is incremented for each loop start and stop.
        # It is used to distinguish queued Qt events from prior or stopped
        # runs of self.
        self._event_notifier_version: int = 0

        # Any exception raised by self._process_asyncio_events is stored
        # in _event_processor_error to be propagated to the caller of
        # self.run_forever, because QEventLoop.exec() does not propagate
        # exceptions.  Exceptions raised by tasks are normally not
        # propagated except for SystemExit and KeyboardInterrupt.
        self._event_processor_error: Optional[BaseException] = None

    # =========================================================================
    # Custom method for AsyncSlot
    # =========================================================================

    def run_task(self, coro, *, name=None):
        raise NotImplementedError

    def _process_asyncio_events(self, event_notifier_version: int):
        """ This slot is connected to the asyncioEventAvailable signal,
        which is emitted whenever asyncio events are possibly available
        and need to be processed."""
        if event_notifier_version != self._event_notifier_version:
            # ignore queued signal from previous or stopped loop run
            return

        assert not self.is_closed(), "unexpectedly closed"
        assert self.is_running(), "unexpectedly stopped"

        if self._stopping:
            if self._qt_event_loop is not None:  # called from run_forever
                self._qt_event_loop.exit(0)
            return

        # Process ready callbacks, ready IO, and scheduled callbacks that
        # have passed the schedule time.  Run only once to avoid starving
        # the Qt event loop.
        try:
            self._run_once()  # defined in asyncio.BaseEventLoop
        except AsyncSlotYield:
            pass
        except BaseException as exc:
            self._event_processor_error = exc
            if self._qt_event_loop is not None:  # called from run_forever
                self._qt_event_loop.exit(1)
            else:
                raise  # TODO: check what to do if called from run_task
        else:
            self._event_notifier.emit(event_notifier_version)

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

        # ---- BEGIN COPIED FROM BaseEventLoop.run_forever
        self._check_closed()
        self._check_running()
        self._set_coroutine_origin_tracking(self._debug)
        self._thread_id = threading.get_ident()

        old_agen_hooks = sys.get_asyncgen_hooks()
        sys.set_asyncgen_hooks(firstiter=self._asyncgen_firstiter_hook,
                               finalizer=self._asyncgen_finalizer_hook)
        # ---- END COPIED FROM BaseEventLoop.run_forever

        # Must make queued connection so that it is handled in QEventLoop
        self._event_notifier_version += 1
        self._event_notifier = _AsyncSlotEventNotifier()
        self._event_notifier.asyncioEventAvailable.connect(
            self._process_asyncio_events, QtCore.Qt.QueuedConnection)
        self._event_notifier.asyncioEventAvailable.emit(
            self._event_notifier_version)

        try:
            events._set_running_loop(self)
            self._qt_event_loop = QtCore.QEventLoop()
            exit_code = self._qt_event_loop.exec()
            if exit_code != 0:
                # propagate exception from _process_asyncio_events
                assert self._event_processor_error is not None
                raise self._event_processor_error  # TODO: test this
        finally:
            self._event_processor_error = None
            self._qt_event_loop = None
            self._event_notifier_version += 1
            self._event_notifier.asyncioEventAvailable.disconnect()
            self._event_notifier = None
            # ---- BEGIN COPIED FROM BaseEventLoop.run_forever
            self._stopping = False
            self._thread_id = None
            events._set_running_loop(None)
            self._set_coroutine_origin_tracking(False)
            sys.set_asyncgen_hooks(*old_agen_hooks)
            # ---- END COPIED FROM BaseEventLoop.run_forever

    # run_until_complete = BaseEventLoop.run_until_complete
    # stop = BaseEventLoop.stop
    # is_running = BaseEventLoop.is_running
    # is_closed = BaseEventLoop.is_closed
    # close = BaseEventLoop.close
    # shutdown_asyncgens = BaseEventLoop.shutdown_asyncgens
    # shutdown_default_executor = BaseEventLoop.shutdown_default_executor

    # -------------------------------------------------------------------------
    # Methods scheduling callbacks.  All these return Handles.
    # -------------------------------------------------------------------------

    # _timer_handle_cancelled: see BaseEventLoop
    # call_soon: see BaseEventLoop
    # call_later: see BaseEventLoop
    # call_at: see BaseEventLoop
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

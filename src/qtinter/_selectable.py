"""Define the communication interface between event loop and selector."""

from typing import Any, Optional


__all__ = '_QiNotifier', '_QiSelectable',


class _QiNotifier:
    """An object responsible for the communication between a QiBaseEventLoop
    object and a _QiSelectable object."""

    def no_result(self) -> Any:
        """Called by the selectable object if no result is immediately
        available for a select() call.  Its return value is returned
        to the caller."""
        raise NotImplementedError

    def notify(self) -> None:
        """Called by the selectable object (in a separate thread) to
        notify that result is available from the last select() call."""
        raise NotImplementedError

    def wakeup(self) -> None:
        """Called by the selectable object wake up an in-progress select()
        in the worker thread."""
        raise NotImplementedError

    def close(self) -> None:
        """Called by the event loop to close the notifier object.  After
        this call, no more notifications will be received."""
        raise NotImplementedError


class _QiSelectable:
    """Protocol for a 'selector' that supports non-blocking select and
    notification.

    A selector may be in one of the following states:
      - IDLE   : the selector is not in BUSY or CLOSED state
      - BUSY   : the last call to select() raised QiYield, and
                 a thread worker is waiting for IO or timeout
      - CLOSED : close() has been called

    State machine:
      - [start] --- __init__ --> IDLE
      - IDLE --- close() --> CLOSED
        IDLE --- select
                 - (IO ready, timeout == 0, or notifier is None) --> IDLE
                 - (IO not ready, timeout != 0, and notifier not None) --> BUSY
        IDLE --- set_notifier --> IDLE
      - BUSY --- (IO ready or timeout reached) --> IDLE
        BUSY --- set_notifier --> (wakes up selector) --> IDLE
      - CLOSED --- [end]
    """

    def set_notifier(self, notifier: Optional[_QiNotifier]) -> None:
        """Set the notifier.

        If the selector is in BUSY state, wake it up and wait for it
        to become IDLE before returning.  In this case, the previous
        installed notifier (if any) is still signaled.
        """
        raise NotImplementedError

    def select(self, timeout: Optional[float] = None):
        """
        If timeout is zero or some IO is readily available, return the
        available IO immediately.

        If timeout is not zero, IO is not ready and notifier is not None,
        launch a thread worker to perform the real select() and return
        notifier.no_result(), which possibly throws.  When the real select()
        completes, signal the notifier object.

        If timeout is not zero, IO is not ready and notifier is None,
        perform normal (blocking) select.
        """
        raise NotImplementedError

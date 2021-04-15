import time

from qtpy.QtCore import QObject, Signal
from qtpy.QtNetwork import QTcpSocket

# #############  QFuture   (mostly borrowed from concurrent futures)


class CancelledError(Exception):
    """The Future was cancelled."""


class InvalidStateError(Exception):
    """The operation is not allowed in this state."""


class QFuture(QObject):
    finished = Signal()

    # Possible future states (for internal use only).
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"  # The future was cancelled by the user...
    # ...and _Waiter.add_cancelled() was called by a worker.
    CANCELLED_AND_NOTIFIED = "cancelled_and_notified"
    FINISHED = "finished"

    def __init__(self, socket: QTcpSocket, parent=None):
        super().__init__(parent)
        self._sock = socket
        self._state = self.PENDING
        self._result = None
        self._exception = None

    def __repr__(self):
        name = self.__class__.__name__
        if self._state == self.FINISHED:
            if self._exception:
                extra = f" raised {self._exception.__class__.__name__}"
            else:
                extra = f" returned {self._result.__class__.__name__}"
        else:
            extra = ""

        return f"<{name} at {id(self)} state={self._state}{extra}>"

    def cancel(self):
        raise NotImplementedError

    def cancelled(self):
        """Return True if the future was cancelled."""
        return self._state in {self.CANCELLED, self.CANCELLED_AND_NOTIFIED}

    def running(self):
        """Return True if the future is currently executing."""
        with self._condition:
            return self._state == self.RUNNING

    def done(self):
        """Return True of the future was cancelled or finished executing."""
        return self._state in {
            self.CANCELLED,
            self.CANCELLED_AND_NOTIFIED,
            self.FINISHED,
        }

    def add_done_callback(self, fn):
        self.finished.connect(fn)

    def __get_result(self):
        if self._exception:
            raise self._exception
        else:
            return self._result

    def result(self, timeout=6):
        """Return the result of the call that the future represents.

        Parameters
        ----------
        timeout: int
            The number of seconds to wait for the result if the future isn't done.
            If None, then there is no limit on the wait time.

        Returns
        -------
        result : Any
            The result of the call that the future represents.

        Raises
        ------
        CancelledError
            If the future was cancelled.
        TimeoutError
            If the future didn't finish executing before the given timeout.
        Exception
            If the call raised then that exception will be raised.
        """
        if self.cancelled():
            raise CancelledError()
        elif self._state == self.FINISHED:
            return self.__get_result()

        t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout:
            if self.cancelled():
                raise CancelledError()
            elif self._state == self.FINISHED:
                return self.__get_result()
            passed = time.perf_counter() - t0
            if not self._sock.waitForReadyRead(int((timeout - passed) * 1000)):
                return
        raise TimeoutError

    def set_result(self, result):
        """Sets the return value of work associated with the future.

        Should only be used by Executor implementations and unit tests.
        """
        if self.done():
            raise InvalidStateError("{}: {!r}".format(self._state, self))
        self._result = result
        self._state = self.FINISHED
        self.finished.emit()

    def set_exception(self, exception):
        """Sets the result of the future as being the given exception.

        Should only be used by Executor implementations and unit tests.
        """
        if self.done():
            raise InvalidStateError("{}: {!r}".format(self._state, self))
        self._exception = exception
        self._state = self.FINISHED
        self.finished.emit()

import atexit
from concurrent.futures import Future
from typing import Any, TypeVar

from loguru import logger
from qtpy.QtCore import QObject, QThread, Signal

_T = TypeVar("_T")


def _build_worker_class(cls):
    assert isinstance(cls, type)

    def _init(self, *args, **kwargs):
        QObject.__init__(self)
        cls.__init__(self, *args, **kwargs)

    def _process_command(
        obj: QObject, name: str, args: tuple, kwargs: dict, future: Future
    ):
        logger.debug(f"{future}, {name}, {args}, {kwargs}")
        if future.set_running_or_notify_cancel():
            try:
                attr = getattr(obj, name)
                result = attr(*args, **kwargs) if callable(attr) else attr
                future.set_result(result)
            except Exception as err:
                logger.error(f"Error executing method {name}: {err}")
                future.set_exception(err)
        else:
            logger.debug("Future was canceled")

    return type(
        cls.__name__,
        (cls, QObject),
        {"__init__": _init, "_process_command": _process_command},
    )


class Controller(QObject):
    _command_ready = Signal(str, tuple, dict, Future)

    def __init__(self, cls: _T, *args, parent: QObject = None, **kwargs) -> None:
        super().__init__(parent=parent)
        atexit.register(self.close)
        _cls = _build_worker_class(cls)

        self.worker = _cls(*args, **kwargs)
        print(self.worker.thread())
        self._worker_dir = set(dir(self.worker))

        self.workerThread = QThread(self)
        self.worker.moveToThread(self.workerThread)
        print(self.worker.thread())

        self.workerThread.finished.connect(self.worker.deleteLater)
        self._command_ready.connect(self.worker._process_command)

        self.workerThread.start()

    def close(self):
        self.workerThread.quit()
        self.workerThread.wait()
        self.deleteLater()

    def __dir__(self):
        return set(object.__dir__(self)).union(self._worker_dir)

    def setProperty(self, *args):
        # conflicts with QObject.setProperty
        return self.__getattr__("setProperty")(*args)

    def submit(self, name: str, args: tuple = (), kwargs: dict = {}) -> Future:
        future: Future[Any] = Future()
        self._command_ready.emit(name, args, kwargs, future)
        return future

    def __getattr__(self, name: str):
        attr = getattr(self.worker, name, None)

        if attr is not None:
            if callable(attr):

                def _proxy(*args, **kwargs):
                    future = self.submit(name, args, kwargs)
                    return future.result()

                return _proxy
            else:
                return self.submit("__getattribute__", (name,)).result()

        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name != "worker":
            attr = getattr(self.worker, name, None)

            if attr is not None:
                self._command_ready.emit("__setattr__", (name, value), {}, Future())

        return object.__setattr__(self, name, value)


class T:
    def __init__(self, x=1) -> None:
        self.x = x

    def sum(self, y):
        if y > 10:
            raise ValueError("nope")
        return self.x + y


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication, QPushButton, QSpinBox

    app = QApplication([])
    c = Controller(T)
    sb = QSpinBox()
    sb.show()
    pb = QPushButton()

    def _submit():
        num = int(sb.text())
        c.sum(num)

    pb.clicked.connect(_submit)
    pb.show()
    app.exec_()

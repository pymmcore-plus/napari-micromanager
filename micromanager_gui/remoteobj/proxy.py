import pickle
import sys
import time
from multiprocessing import shared_memory
from pathlib import Path
from typing import Dict, List

import numpy as np
from qtpy.QtNetwork import QTcpSocket

from .qfuture import QFuture


def remove_shm_from_resource_tracker():
    """Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked

    More details at: https://bugs.python.org/issue38119
    """
    from multiprocessing import resource_tracker

    def fix_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(name, rtype)

    resource_tracker.register = fix_register

    def fix_unregister(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.unregister(name, rtype)

    resource_tracker.unregister = fix_unregister

    if "shared_memory" in resource_tracker._CLEANUP_FUNCS:
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]


def _prep_packet(obj, format):
    """serialize and prefix object."""
    import struct

    msg = pickle.dumps(obj, protocol=-1)
    return struct.pack(format, len(msg)) + msg


class RemoteProxy:
    def __init__(
        self, obj, *args, host="127.0.0.1", port=54145, prefix_format=">L", **kwargs
    ):
        self._obj_ = obj
        self._host = host
        self._port = port
        self._prefix_format = prefix_format
        self._futures: Dict[int, QFuture] = {}
        self._shm = None

        # atexit.register(self.disconnect)

        self._sock = QTcpSocket()
        self._sock.readyRead.connect(self._on_read_ready)
        self._connect()
        self._sock.error.connect(self._on_error)
        self._create_remote_object(args, kwargs)

    def _connect(self, retries=6, interval=100):
        if not self._sock.state():
            self._sock.connectToHost(self._host, self._port)
            self._sock.waitForConnected()
            if retries:
                time.sleep(interval / 1000)  # TODO: don't block
                return self._connect(retries=retries - 1)
            raise TimeoutError

    def _on_read_ready(self):
        # TODO: cleanup and make protocols more explicit

        if not self._sock.bytesAvailable():
            return

        msg = self._sock.read(self._sock.bytesAvailable())
        obj = pickle.loads(msg)
        if "fid" in obj:
            future = self._futures.pop(obj["fid"])
            if "err" in obj:
                future.set_exception(obj["err"][1])
                return
            if "shm_name" in obj:
                self._shm = shared_memory.SharedMemory(
                    name=obj["shm_name"], create=False
                )
                b = np.ndarray(obj["shape"], dtype=obj["dtype"], buffer=self._shm.buf)
                future.set_result(b)
            else:
                future.set_result(obj["result"])
        else:
            print(obj, "has no future")

    def _on_error(self, error):
        if error == QTcpSocket.RemoteHostClosedError:
            print("remove closed")
        elif error == QTcpSocket.HostNotFoundError:
            print(" host was not found.")
        elif error == QTcpSocket.ConnectionRefusedError:
            print("connection refused")
        else:
            print(self._sock.errorString())

    def __dir__(self):
        return object.__dir__(self) + dir(self._obj_)

    def _create_remote_object(self, args=(), kwargs={}):
        self.send(
            "CREATE",
            module=self._obj_.__module__,
            name=self._obj_.__name__,
            args=args,
            kwargs=kwargs,
        )

    def send(self, command, **kwargs):
        if not self._sock.state():
            return
        future = QFuture(self._sock)
        fid = id(future)
        self._futures[fid] = future
        obj = {"obj_id": id(self), "cmd": command, "fid": fid, **kwargs}

        packet = _prep_packet(obj, self._prefix_format)
        self._sock.write(packet)
        return future

    def disconnect(self):
        if not self._sock.state():
            return
        if self._shm is not None:
            self._shm.close()
        f = self.send("CLOSE", shm=[self._shm.name] if self._shm else [])
        if f.result() != "ok":
            import warnings

            warnings.warn("Server did not clean up shared memory")
        self._sock.disconnectFromHost()
        self._sock.disconnected.connect(self._sock.deleteLater)

    def __getattr__(self, name: str):
        attr = getattr(self._obj_, name, None)
        if attr is not None:
            if not callable(attr):
                raise AttributeError(f"{self._obj_} has no callable attribute {name!r}")

            def _proxy(*args, **kwargs):
                return self.send("ROBJ", attr=name, args=args, kwargs=kwargs)

            return _proxy
        return object.__getattribute__(self, name)


class RemoteObjectServer:
    SERVER = str(Path(__file__).parent / "server2.py")

    def __init__(self, host="127.0.0.1", port=54145, prefix_format=">L"):
        self.port = port
        self.host = host
        self.prefix_format = prefix_format
        self._proxies: List[RemoteProxy] = []
        remove_shm_from_resource_tracker()
        self._proc = None
        if not self.ping():
            from subprocess import Popen

            self._proc = Popen(
                args=[
                    sys.executable,
                    self.SERVER,
                    "--port",
                    str(port),
                    "--host",
                    host,
                    "--prefix-format",
                    prefix_format,
                ]
            )

    def ping(self) -> bool:
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(_prep_packet({"cmd": "PING"}, self.prefix_format))
                msg = pickle.loads(s.recv(100))
                if msg.get("status") == "OK":
                    return True
        except ConnectionError:
            pass
        return False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback) -> None:
        import signal

        while self._proxies:
            self._proxies.pop().disconnect()

        if self._proc is not None:
            print("SEND ITERR", self._proc)
            self._proc.send_signal(signal.SIGINT)
            return self._proc.__exit__(type, value, traceback)

    def create(self, cls):
        p = RemoteProxy(
            cls, host=self.host, port=self.port, prefix_format=self.prefix_format
        )
        self._proxies.append(p)
        return p


if __name__ == "__main__":

    from pymmcore import CMMCore

    with RemoteObjectServer() as ro:
        sp = ro.create(CMMCore)
        mm = Path("/Applications/Micro-Manager-2.0.0-gamma1-20210330/")
        sp.setDeviceAdapterSearchPaths([str(mm)])
        sp.loadSystemConfiguration(str(mm / "MMConfig_demo.cfg"))
        sp.setConfig("Channel", "Cy5")
        sp.snapImage()
        sp.snapImage()
        sp.snapImage()
        print(sp.getImage().result())

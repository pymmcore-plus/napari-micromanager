import importlib
import pickle
import socket
import struct
import sys
import time
from multiprocessing import shared_memory
from threading import Thread
from typing import Dict, Tuple

import numpy as np
from loguru import logger
from tblib import pickling_support

pickling_support.install()

logger.remove()
FMT = (
    "<g>{time:HH:mm:ss.SSS}</g> "
    "| <lvl>{level: <7}</lvl> | "
    "<c>{function}</c>:<c>{line}</c> - "
    "<lvl>{message}</lvl>"
)
logger.add(sys.stderr, format=FMT)


SHARED_MEM = []
_OBJECT_STORE: Dict[int, object] = {}
CREATE = "$CREATE"
DISCONNECT = "$DISCONNECT"


def create_object(obj_id, module, name, args, kwargs, **_):
    if obj_id not in _OBJECT_STORE:
        mod = importlib.import_module(module)
        obj = getattr(mod, name)(*args, **kwargs)
        _OBJECT_STORE[obj_id] = obj
    return _OBJECT_STORE[obj_id]


def execute(msg: dict):
    try:
        time.sleep(0.1)
        cmd = msg["cmd"]
        if cmd == CREATE:
            obj = create_object(msg["obj_id"], **msg["kwargs"])
            return {**msg, "result": None}

        obj = _OBJECT_STORE[msg["obj_id"]]
        result = getattr(obj, cmd)(*msg["args"], **msg["kwargs"])
        if isinstance(result, np.ndarray):
            shm = shared_memory.SharedMemory(create=True, size=result.nbytes)
            b = np.ndarray(result.shape, dtype=result.dtype, buffer=shm.buf)
            b[:] = result[:]
            SHARED_MEM.append(shm)
            return {
                "fid": msg["fid"],
                "shape": result.shape,
                "dtype": str(result.dtype),
                "shm_name": shm.name,
            }

        return {"fid": msg["fid"], "result": result}
    except Exception:
        type, value, tb = sys.exc_info()
        try:
            if isinstance(value, RuntimeError):
                value = RuntimeError(value.args[0].getMsg())  # type: ignore
        except Exception:
            pass
        return {**msg, "err": (type, value, tb)}


Address = Tuple[str, int]


def monitor_client(conn: socket.socket, addr: Address, prefix_format=">L"):
    # prefix_format = bytes of each message containing message size
    logger.debug("creating thread")
    prefix_len = len(struct.pack(prefix_format, 0))
    with conn:
        while True:
            try:
                nbytes = conn.recv(prefix_len)
            except ConnectionResetError:
                logger.warning("Connection reset by peer")
                break

            if not nbytes:
                break
            if nbytes == b"PING":
                msg = {"status": "ok", "prefix_format": prefix_format}
                conn.sendall(pickle.dumps(msg, protocol=-1))
                continue

            data = conn.recv(struct.unpack(prefix_format, nbytes)[0])

            msg = pickle.loads(data)
            logger.debug("<<< {}", repr(msg))

            if msg.get("cmd") == DISCONNECT:
                name = msg.get("args")[0]  # FIXME
                if name is not None:
                    shm = shared_memory.SharedMemory(name=name, create=False)
                    logger.debug("unlink shared memory {}", shm.name)
                    shm.close()
                    shm.unlink()
                conn.sendall(pickle.dumps({**msg, "result": "ok"}))
                break

            response = execute(msg)
            logger.debug(">>> {}", repr(response))
            try:
                conn.sendall(pickle.dumps(response, protocol=-1))
            except ConnectionError as e:
                logger.warning("Error sending data back to client {}", e)
                break
    logger.info("Closing connection: {}:{}", addr[0], addr[1])


def listen(s: socket.socket, host, port, max_connections=4, prefix_format=">L"):
    s.bind((host, port))
    s.listen(max_connections)
    logger.info("Server ready at:  {}:{}", host, port)
    while True:
        conn, addr = s.accept()
        logger.info("Client connected: {}:{}", addr[0], addr[1])
        # monitor_client(conn, addr, prefix_format)
        Thread(target=monitor_client, args=(conn, addr, prefix_format)).start()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Script to learn basic argparse")
    parser.add_argument("-n", "--host", help="host ip", default="127.0.0.1")
    parser.add_argument("-p", "--port", help="socket port", default="54145", type=int)
    parser.add_argument(
        "-c", "--max-connections", help="max number of clients", default="4", type=int
    )
    parser.add_argument(
        "--prefix-format", help="message length prefix format", default=">L"
    )

    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listen(s, args.host, args.port, args.max_connections, args.prefix_format)
        except KeyboardInterrupt:
            logger.warning("Interrupt received")

    for shm in SHARED_MEM:
        try:
            logger.debug("cleaning up {}", shm.name)
            shm.close()
            shm.unlink()
        except FileNotFoundError:
            pass
    logger.info("Server closing")

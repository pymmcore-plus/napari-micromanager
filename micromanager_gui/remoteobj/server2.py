import importlib
import pickle
import struct
import sys
from itertools import count
from multiprocessing import shared_memory
from typing import Dict, Optional, Tuple

import numpy as np
import trio
from loguru import logger
from tblib import pickling_support


class MessageReceiver:
    _RECEIVE_SIZE = 1024

    def __init__(
        self,
        stream: Optional[trio.abc.ReceiveStream] = None,
        buffer: bytes = b"",
        prefix_format: str = ">L",
        max_frame_length: int = 16384,
    ):
        assert not stream or isinstance(stream, trio.abc.ReceiveStream)
        assert isinstance(buffer, bytes)

        self.stream = stream
        self.prefix_format = prefix_format
        self.prefix_length = len(struct.pack(prefix_format, 0))
        self.max_frame_length = max_frame_length

        self._buf = bytearray(buffer)
        self._next_find_idx = 0

    def __bool__(self):
        return bool(self._buf)

    async def receive_exactly(self, n: int) -> bytes:
        while len(self._buf) < n:
            await self._receive()

        return self._frame(n)

    async def _receive(self):
        if len(self._buf) > self.max_frame_length:
            raise ValueError("frame too long")

        more_data = (
            await self.stream.receive_some(self._RECEIVE_SIZE)
            if self.stream is not None
            else b""
        )
        if more_data == b"":
            if self._buf:
                raise ValueError("incomplete frame")
            raise trio.EndOfChannel

        self._buf += more_data

    def _frame(self, idx: int) -> bytes:
        frame = self._buf[:idx]
        del self._buf[:idx]
        self._next_find_idx = 0
        return frame

    async def _receive_prefix(self) -> int:
        prefix = await self.receive_exactly(self.prefix_length)
        if not prefix:
            raise StopAsyncIteration
        return struct.unpack(self.prefix_format, prefix)[0]

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            msg_length = await self._receive_prefix()
            data = await self.receive_exactly(msg_length)
            if not data:
                raise StopAsyncIteration
        except trio.EndOfChannel:
            raise StopAsyncIteration
        return data


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


class InvalidProtocolError(Exception):
    pass


Address = Tuple[str, int]


CONNECTION_COUNTER = count()


class Handler:
    def handle(self, data: bytes, cnx_id: int):
        obj = parse_message(data)
        try:
            cmd = obj["cmd"]
            logger.debug("<-- {}: {}", cmd, obj)
            result = getattr(self, cmd.lower())(obj, cnx_id)
        except KeyError as e:
            raise InvalidProtocolError(f"Invalid command: {e}")
        logger.debug("--> {}", result)
        return encode_message(result)

    def ping(self, obj, cnx_id):
        return {"status": "OK", **obj}

    def close(self, obj, cnx_id):
        for shm_name in obj.get("shm") or []:
            shm = shared_memory.SharedMemory(name=shm_name, create=False)
            logger.debug("unlink shared memory {}", shm.name)
            shm.close()
            shm.unlink()
        return {**obj, "result": "ok"}

    def robj(self, msg, cnx_id):
        try:

            obj = _OBJECT_STORE[msg["obj_id"]]
            result = getattr(obj, msg["attr"])(*msg["args"], **msg["kwargs"])
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

    def create(self, obj, cnx_id):
        client_id = obj["obj_id"]
        if client_id not in _OBJECT_STORE:
            mod = importlib.import_module(obj["module"])
            new = getattr(mod, obj["name"])(*obj["args"], **obj["kwargs"])
            logger.debug(f"Created new remote object: {new!r}")
            _OBJECT_STORE[client_id] = new
        return {**obj, "result": None}


def parse_message(data: bytes) -> dict:
    return pickle.loads(data)


def encode_message(obj: dict) -> bytes:
    return pickle.dumps(obj, protocol=-1)


async def echo_server(server_stream: trio.SocketStream):
    cnx_id = next(CONNECTION_COUNTER)
    logger.info(f"echo_server {cnx_id}: started")
    try:
        handler = Handler()
        async for message in MessageReceiver(server_stream):
            response = handler.handle(message, cnx_id=cnx_id)
            await server_stream.send_all(response)
            await trio.sleep(.5)
        logger.info(f"echo_server {cnx_id}: connection closed")
    except Exception as exc:
        logger.error(f"echo_server {cnx_id}: crashed: {exc!r}")


async def main(host, port, max_conn, prefix_format):
    logger.info("Server ready at:  {}:{}", host, port)
    try:
        await trio.serve_tcp(echo_server, port)
    except KeyboardInterrupt:
        logger.warning("Interrupt received")


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

    try:
        trio.run(main, args.host, args.port, args.max_connections, args.prefix_format)
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

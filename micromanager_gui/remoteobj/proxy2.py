import pickle
import sys
from itertools import count
from typing import List

import trio
from loguru import logger


def _prep_packet(obj, format=">L"):
    """serialize and prefix object."""
    import struct

    msg = pickle.dumps(obj, protocol=-1)
    return struct.pack(format, len(msg)) + msg


class RemoteObjectClient:
    def __init__(self, port=54145, host="127.0.0.1"):
        self.port = port
        self.host = host
        self._send_counter = count()
        self._store = []
        self._stream = None

    async def connect(self):
        self._stream = await trio.open_tcp_stream(self.host, self.port)

    async def sender(self):
        if not self._stream:
            raise RuntimeError("connect to stream first")
        logger.info("sender: started!")
        for i in self._send_counter:
            obj = {"cmd": "PING", "id": i}
            logger.debug(f"sender: sending {obj!r}")
            await self._stream.send_all(_prep_packet(obj))
            if not i % 6:
                while i not in self._store:
                    await trio.sleep(0.1)
            await trio.sleep(0.1)

    async def receiver(self):
        if not self._stream:
            raise RuntimeError("connect to stream first")
        logger.info("receiver: started!")
        async for data in self._stream:
            resp = pickle.loads(data)
            self._store.append(resp["id"])
            logger.debug(f"receiver: got data {resp!r}")
        logger.info("receiver: connection closed")

    async def go(self):
        print(f"parent: connecting to 127.0.0.1:{self.port}")
        async with trio.open_nursery() as nursery:
            print("parent: spawning sender...")
            nursery.start_soon(self.sender)
            print("parent: spawning receiver...")
            nursery.start_soon(self.receiver)

    async def disconnect(self):
        await self._stream.aclose()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()


async def main():
    async with RemoteObjectClient() as roc:
        await roc.go()


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
        trio.run(main)
    except KeyboardInterrupt:
        logger.warning("Interrupt received")

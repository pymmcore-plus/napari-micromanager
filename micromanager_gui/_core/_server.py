import re

from micromanager_gui._core._mmcore_plus import MMCorePlus
from micromanager_gui._core._serialize import register_serializers
from micromanager_gui._core._util import wrap_for_pyro
from Pyro5.api import behavior, expose, oneway, serve

CORE_NAME = "mmgui.cmmcore"


camel_to_snake = re.compile(r"(?<!^)(?=[A-Z])")


@expose
@behavior(instance_mode="single")
@wrap_for_pyro
class pyroCMMCore(MMCorePlus):
    def __init__(self, adapter_paths=None):
        super().__init__(adapter_paths=adapter_paths)
        self._callback_handlers = set()

    @oneway
    def run_mda(self, sequence) -> None:
        return super().run_mda(sequence)

    @oneway
    def connect_callback_handler(self, handler):
        self._callback_handlers.add(handler)

    @oneway
    def emit_signal(self, signal_name, *args):
        snaked = camel_to_snake.sub("_", signal_name).lower()
        for handler in self._callback_handlers:
            handler._pyroClaimOwnership()
            handler.emit(snaked, args)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=54333, help="port")
    parser.add_argument("--host", default="localhost")
    args = parser.parse_args()

    register_serializers()

    serve({pyroCMMCore: CORE_NAME}, use_ns=False, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

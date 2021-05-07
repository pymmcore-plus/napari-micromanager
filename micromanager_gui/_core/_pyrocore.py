import re

from micromanager_gui._core._mmcore_plus import MMCorePlus
from micromanager_gui._core._util import wrap_for_pyro
from Pyro5.api import behavior, expose, oneway

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
    def connect_remote_callback(self, handler):
        self._callback_handlers.add(handler)

    @oneway
    def emit_signal(self, signal_name, *args):
        super().emit_signal(signal_name, *args)
        snaked = camel_to_snake.sub("_", signal_name).lower()
        for handler in self._callback_handlers:
            handler._pyroClaimOwnership()
            handler.emit(snaked, args)

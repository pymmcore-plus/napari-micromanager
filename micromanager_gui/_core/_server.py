from Pyro5.api import behavior, expose, serve

from ._mmcore_plus import MMCorePlus
from ._util import wrap_for_pyro

pyroCMMCore = wrap_for_pyro(MMCorePlus)
single_instance = behavior(instance_mode="single")
CMMCore = expose(single_instance(pyroCMMCore))


if __name__ == "__main__":
    from ._serialize import register_serializers

    register_serializers()
    serve({CMMCore: "mmgui.cmmcore"}, use_ns=False, host="127.0.0.1", port=54333)

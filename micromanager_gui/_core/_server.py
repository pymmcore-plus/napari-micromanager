from micromanager_gui._core._mmcore_plus import MMCorePlus
from micromanager_gui._core._serialize import register_serializers
from micromanager_gui._core._util import wrap_for_pyro
from Pyro5.api import behavior, expose, serve

CORE_NAME = "mmgui.cmmcore"


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=54333, help="port")
    parser.add_argument("--host", default="localhost")
    args = parser.parse_args()

    register_serializers()

    pyroCMMCore = wrap_for_pyro(MMCorePlus)
    single_instance = behavior(instance_mode="single")
    CMMCore = expose(single_instance(pyroCMMCore))

    serve({CMMCore: CORE_NAME}, use_ns=False, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

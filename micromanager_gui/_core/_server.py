from micromanager_gui._core._pyrocore import pyroCMMCore
from micromanager_gui._core._serialize import register_serializers
from Pyro5.api import serve

CORE_NAME = "mmgui.cmmcore"


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=54333, help="port")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    register_serializers()

    serve({pyroCMMCore: CORE_NAME}, use_ns=False, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

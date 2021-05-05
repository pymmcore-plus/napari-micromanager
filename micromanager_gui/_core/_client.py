import sys

import Pyro5.errors
from micromanager_gui._core._serialize import register_serializers
from Pyro5.api import Proxy

register_serializers()


sys.excepthook = Pyro5.errors.excepthook

HOST = "127.0.0.1"
PORT = 54333
objname = "mmgui.cmmcore"

core = Proxy(f"PYRO:{objname}@{HOST}:{PORT}")
core.loadSystemConfiguration()
core.snapImage()
a = core.getImage()
print("arr", a.shape, a.dtype, a.mean())
print(a)

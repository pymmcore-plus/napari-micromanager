from __future__ import annotations

import subprocess
import sys
import time
from typing import TYPE_CHECKING

from Pyro5 import api, core

from . import _server
from ._serialize import register_serializers

if TYPE_CHECKING:
    from micromanager_gui._core._mmcore_plus import MMCorePlus


class detatched_mmcore(subprocess.Popen):
    """Subprocess that runs an MMCore server via Pyro"""

    def __init__(self, host="127.0.0.1", port=54333, timeout=5, config=None) -> None:
        self._host = host
        self._port = port
        cmd = [sys.executable, _server.__file__, "-p", str(port), "--host", host]
        super().__init__(cmd)  # type: ignore

        register_serializers()
        self._wait_for_daemon(timeout)
        self._core = api.Proxy(f"PYRO:{_server.CORE_NAME}@{self._host}:{self._port}")
        if config:
            self._core.loadSystemConfiguration(config)

    def _wait_for_daemon(self, timeout=5):
        daemon = api.Proxy(f"PYRO:{core.DAEMON_NAME}@{self._host}:{self._port}")
        while timeout > 0:
            try:
                daemon.ping()
                break
            except Exception:
                timeout -= 0.1
                time.sleep(0.1)

    @property
    def core(self) -> MMCorePlus:
        return self._core

    def __exit__(self, *args):
        super().__exit__(*args)

from __future__ import annotations

import atexit
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING

from Pyro5 import api, core
from qtpy.QtCore import QObject, Signal

from . import _server
from ._serialize import register_serializers

if TYPE_CHECKING:
    from micromanager_gui._core._server import pyroCMMCore


class QCoreListener(QObject):
    properties_changed = Signal()
    property_changed = Signal(str, str, object)
    channel_group_changed = Signal(str)
    config_group_changed = Signal(str, str)
    system_configuration_loaded = Signal()
    pixel_size_changed = Signal(float)
    pixel_size_affine_changed = Signal(float, float, float, float, float, float)
    stage_position_changed = Signal(str, float)
    xy_stage_position_changed = Signal(str, float, float)
    exposure_changed = Signal(str, float)
    slm_exposure_changed = Signal(str, float)
    mda_frame_ready = Signal(object, object)

    @api.expose
    def emit(self, signal_name, args):
        emitter = getattr(self, signal_name, None)
        if emitter:
            emitter.emit(*args)


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

        daemon = api.Daemon()
        self.signals = QCoreListener()
        daemon.register(self.signals)
        thread = threading.Thread(target=daemon.requestLoop, daemon=True)
        thread.start()

        self._core.connect_remote_callback(self.signals)
        atexit.register(self.kill)

    def _wait_for_daemon(self, timeout=5):
        remote_daemon = api.Proxy(f"PYRO:{core.DAEMON_NAME}@{self._host}:{self._port}")
        while timeout > 0:
            try:
                remote_daemon.ping()
                break
            except Exception:
                timeout -= 0.1
                time.sleep(0.1)

    @property
    def core(self) -> pyroCMMCore:  # incorrect. but nicer autocompletion
        return self._core

    def __exit__(self, *args):
        super().__exit__(*args)

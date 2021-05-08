import atexit
import subprocess
import sys
import threading
import time

from loguru import logger
from Pyro5 import api, core
from qtpy.QtCore import QObject, Signal

from . import _server
from ._serialize import register_serializers


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
    mda_started = Signal()
    mda_canceled = Signal()
    mda_paused = Signal(bool)
    mda_finished = Signal()

    @api.expose
    def emit(self, signal_name, args):
        emitter = getattr(self, signal_name, None)
        if emitter:
            emitter.emit(*args)


def ensure_server_running(host="127.0.0.1", port=54333, timeout=5):
    uri = f"PYRO:{core.DAEMON_NAME}@{host}:{port}"
    remote_daemon = api.Proxy(uri)
    try:
        remote_daemon.ping()
        logger.debug("Found existing server:\n{}", remote_daemon.info())
    except Exception:
        logger.debug("No server found, creating new mmcore server")
        cmd = [sys.executable, _server.__file__, "-p", str(port), "--host", host]
        proc = subprocess.Popen(cmd)
        while timeout > 0:
            try:
                remote_daemon.ping()
                return proc
            except Exception:
                timeout -= 0.1
                time.sleep(0.1)
        raise TimeoutError(f"Timeout connecting to server {uri}")


class detatched_mmcore:
    _instance = None

    def __init__(self, host="127.0.0.1", port=54333, timeout=5, cleanup=True):
        detatched_mmcore._instance = self
        self._cleanup = cleanup

        register_serializers()
        self.proc = ensure_server_running(host, port, timeout)
        if cleanup and self.proc:
            atexit.register(self.proc.kill)

        self.core = api.Proxy(f"PYRO:{_server.CORE_NAME}@{host}:{port}")
        self.qsignals = QCoreListener()

        self._callback_daemon = api.Daemon()
        self._callback_daemon.register(self.qsignals)
        self.core.connect_remote_callback(self.qsignals)  # must come after register()
        thread = threading.Thread(target=self._callback_daemon.requestLoop, daemon=True)
        thread.start()

    def __enter__(self):
        # FIXME: weird...
        return (self.core, self.qsignals)

    def __exit__(self, *args):
        self.close()

    def close(self):
        logger.debug("closing pyro client")
        self.core.disconnect_remote_callback(self.qsignals)
        self.core._pyroRelease()
        self._callback_daemon.close()
        if self._cleanup and self.proc is not None:
            self.proc.kill()

    @classmethod
    def instance(cls):
        return cls._instance


if __name__ == "__main__":
    with detatched_mmcore() as (mmcore, signals):
        print(mmcore._pyroUri)
        mmcore.loadSystemConfiguration()

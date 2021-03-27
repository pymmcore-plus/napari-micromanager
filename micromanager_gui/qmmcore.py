import logging
import os
import sys
import time
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any

import numpy as np
import pymmcore
from qtpy.QtCore import QObject, Signal
from tqdm import tqdm

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from useq import MDASequence


def patch_swig_errors():
    try:
        from functools import wraps

        from IPython import get_ipython
        from IPython.core.interactiveshell import InteractiveShell

        if not get_ipython():
            raise ImportError()

        def change_function(func):
            @wraps(func)
            def showtraceback(*args, **kwargs):
                # extract exception type, value and traceback
                etype, evalue, tb = sys.exc_info()
                if isinstance(evalue, RuntimeError) and evalue.args:
                    obj = evalue.args[0]
                    if isinstance(obj, pymmcore.CMMError):
                        evalue = RuntimeError(obj.getMsg())
                    return func(*args, exc_tuple=(etype, evalue, tb), **kwargs)
                # otherwise run the original hook
                return func(*args, **kwargs)

            return showtraceback

        InteractiveShell.showtraceback = change_function(InteractiveShell.showtraceback)
    except ImportError:
        ehook = sys.excepthook

        def swig_hook(typ, value, tb):
            if isinstance(value, RuntimeError) and value.args:
                obj = value.args[0]
                if isinstance(obj, pymmcore.CMMError):
                    value = RuntimeError(obj.getMsg())
            ehook(typ, value, tb)

        sys.excepthook = swig_hook


def find_micromanager():
    """Locate a Micro-Manager folder (for device adapters)."""
    # environment variable takes precedence
    env_path = os.getenv("MICROMANAGER_PATH")
    if env_path and os.path.isdir(env_path):
        logger.debug(f"using MM path from env var: {env_path}")
        return env_path
    # then look for an installation in this folder (use `install_mm.sh` to install)
    sfx = "_win" if os.name == "nt" else "_mac"
    local_install = list(Path(__file__).parent.glob(f"Micro-Manager*{sfx}"))
    if local_install:
        logger.debug(f"using MM path from env var: {local_install[0]}")
        return str(local_install[0])

    # lastly, look in the applications folder
    try:
        if sys.platform == "darwin":
            return str(next(Path("/Applications/").glob("Micro-Manager*")))

        if sys.platform == "win32":
            return str(next(Path("C:/Program Files/").glob("Micro-Manager*")))

        raise NotImplementedError(
            f"MM autodiscovery not implemented for platform: {sys.platform}"
        )
    except StopIteration:
        logger.error("could not find micromanager directory")


class QMMCore(QObject):
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

    __instance = None

    stack_to_viewer = Signal(np.ndarray, int, int)

    # Singleton pattern: https://python-patterns.guide/gang-of-four/singleton/
    def __new__(cls) -> pymmcore.CMMCore:
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._initialized = False
        return cls.__instance

    def __init__(self, adapter_paths=None):
        if self._initialized:
            return
        super().__init__()
        patch_swig_errors()
        self._mmc = pymmcore.CMMCore()
        if not adapter_paths:
            adapter_paths = [find_micromanager()]
        self.setDeviceAdapterSearchPaths(adapter_paths)

        self._callback = CallbackRelay(self)
        self._mmc.registerCallback(self._callback)
        self._initialized = True
        self.system_configuration_loaded.connect(self._on_system_configuration_loaded)

    def _on_system_configuration_loaded(self):
        for g in self._mmc.getAvailableConfigGroups():
            if g.lower() == "channel":
                self._mmc.setChannelGroup(g)
                break

    def setDeviceAdapterSearchPaths(self, adapter_paths):
        # add to PATH as well for dynamic dlls
        logger.info(f"setting adapter search paths: {adapter_paths}")
        env_path = os.environ["PATH"]
        for p in adapter_paths:
            if p not in env_path:
                env_path = p + os.pathsep + env_path
        os.environ["PATH"] = env_path
        self._mmc.setDeviceAdapterSearchPaths(adapter_paths)

    def __getattr__(self, name):
        return getattr(self._mmc, name)

    def __dir__(self):
        return set(object.__dir__(self)).union(dir(self._mmc))

    def loadSystemConfiguration(self, file="demo"):
        if file.lower() == "demo":
            file = (Path(find_micromanager()) / "MMConfig_demo.cfg").resolve()
        logger.info(f"loading config at {file}")
        self._mmc.loadSystemConfiguration(str(file))

    def setProperty(self, device_label: str, property: str, value: Any):
        # conflicts with QObject.setProperty
        logger.debug(f"Setting {device_label}.{property} = {value!r}")
        return self._mmc.setProperty(device_label, property, value)

    @property
    def setQProperty(self):
        # conflicts with MMCore.setProperty
        return QObject.setProperty

    def setRelPosition(self, dx=0, dy=0, dz=0):
        if dx or dy:
            x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
            self._mmc.setXYPosition(x + dx, y + dy)
        if dz:
            z = self._mmc.getPosition(self._mmc.getFocusDevice())
            self.setZPosition(z + dz)
        self._mmc.waitForDevice(self._mmc.getXYStageDevice())
        self._mmc.waitForDevice(self._mmc.getFocusDevice())

    def getZPosition(self):
        return self._mmc.getPosition(self._mmc.getFocusDevice())

    def setZPosition(self, val):
        return self._mmc.setPosition(self._mmc.getFocusDevice(), val)

    def run_mda(self, experiment: "MDASequence"):

        print(f"running {repr(experiment)}")

        t0 = time.perf_counter()  # reference time, in seconds
        progress = tqdm(experiment)  # this gives us a progress bar in the console
        for frame in progress:
            elapsed = time.perf_counter() - t0
            target = frame.t / 1000
            wait_time = target - elapsed
            if wait_time > 0:
                progress.set_description(f"waiting for {wait_time}")
                time.sleep(wait_time)
            progress.set_description(f"{frame}")
            xpos, ypos, z_midpoint = frame.p
            channel_name, exposure_ms = frame.c

            self._mmc.setXYPosition(xpos, ypos)
            self._mmc.setPosition("Z_Stage", z_midpoint + frame.z)
            self._mmc.setExposure(exposure_ms)
            self._mmc.setConfig("Channel", channel_name)
            self._mmc.snapImage()
            img = self._mmc.getImage()

            self.stack_to_viewer.emit(img, frame)

        summary = """
        ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
        {}
        Finished in: {} Seconds
         ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲
        """.format(
            str(experiment), round(time.perf_counter() - t0, 4)
        )
        print(dedent(summary))


class CallbackRelay(pymmcore.MMEventCallback):
    def __init__(self, emitter):
        super().__init__()
        self._emitter = emitter

    def onPropertiesChanged(self):
        self._emitter.properties_changed.emit()

    def onPropertyChanged(self, dev_name: str, prop_name: str, prop_val: str):
        self._emitter.property_changed.emit(dev_name, prop_name, prop_val)

    def onChannelGroupChanged(self, new_channel_group_name: str):
        self._emitter.channel_group_changed.emit(new_channel_group_name)

    def onConfigGroupChanged(self, group_name: str, new_config_name: str):
        self._emitter.config_group_changed.emit(group_name, new_config_name)

    def onSystemConfigurationLoaded(self):
        self._emitter.system_configuration_loaded.emit()

    def onPixelSizeChanged(self, new_pixel_size_um: float):
        self._emitter.pixel_size_changed.emit(new_pixel_size_um)

    def onPixelSizeAffineChanged(self, v0, v1, v2, v3, v4, v5):
        self._emitter.pixel_size_affine_changed.emit(v0, v1, v2, v3, v4, v5)

    def onStagePositionChanged(self, name: str, pos: float):
        self._emitter.stage_position_changed.emit(name, pos)

    def onXYStagePositionChanged(self, name: str, xpos: float, ypos: float):
        self._emitter.xy_stage_position_changed.emit(name, xpos, ypos)

    def onExposureChanged(self, name: str, new_exposure: float):
        self._emitter.exposure_changed.emit(name, new_exposure)

    def onSLMExposureChanged(self, name: str, new_exposure: float):
        self._emitter.slm_exposure_changed.emit(name, new_exposure)

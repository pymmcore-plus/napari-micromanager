import logging
import os
import sys
import time
import warnings
from pathlib import Path
from textwrap import dedent

import numpy as np
import pymmcore
from qtpy.QtCore import QObject, Signal
from tqdm import tqdm

logger = logging.getLogger(__name__)

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
    env_path = os.getenv("MICROMANAGER_PATH")
    if env_path and os.path.isdir(env_path):
        return env_path
    try:
        if sys.platform == "darwin":
            mm_path = str(next(Path("/Applications/").glob("Micro-Manager*")))
            return mm_path

        if sys.platform == "win32":
            mm_path = str(next(Path("C:/Program Files/").glob("Micro-Manager-2*")))
            return mm_path

        raise NotImplementedError(
            f"MM autodiscovery not implemented for platform: {sys.platform}"
        )
    except StopIteration:
        return None


class MMCore(QObject):
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
        self._mmc = pymmcore.CMMCore()
        if not adapter_paths:
            adapter_paths = find_micromanager()
        if adapter_paths:
            self._mmc.setDeviceAdapterSearchPaths([adapter_paths])
        else:
            warnings.warn("No adaptor path found! set MICROMANAGER_PATH env var")
        self._callback = CallbackRelay(self)
        self._mmc.registerCallback(self._callback)
        self._initialized = True

    def __getattr__(self, name):
        return getattr(self._mmc, name)

    def __dir__(self):
        return set(object.__dir__(self)).union(dir(self._mmc))

    @property
    def setProperty(self):
        # conflicts with QObject.setProperty
        return self._mmc.setProperty

    def run_mda(self, experiment, stack, cnt):

        if len(self._mmc.getLoadedDevices()) < 2:
            warnings.warn("Cannot run MDA. Load a cfg file first.")
            return

        if not experiment.channels:
            warnings.warn("Cannot run MDA. Select at least one channel.")
            return

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

            t_index = experiment.time_deltas.index(frame.t)
            p_index = experiment.stage_positions.index(frame.p)
            z_index = experiment.z_positions.index(frame.z)
            c_index = experiment.channels.index(frame.c)

            self._mmc.setXYPosition(xpos, ypos)
            self._mmc.setPosition("Z_Stage", z_midpoint + frame.z)
            self._mmc.setExposure(exposure_ms)
            self._mmc.setConfig("Channel", channel_name)
            self._mmc.snapImage()
            img = self._mmc.getImage()

            stack[t_index, z_index, c_index, :, :] = img

            self.stack_to_viewer.emit(stack, cnt, p_index)

        summary = """
        ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
        {}
        Finished in: {} Seconds
         ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲ ̲
        """.format(
            str(experiment), round(time.perf_counter() - t0, 4)
        )
        logger.info(dedent(summary))


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

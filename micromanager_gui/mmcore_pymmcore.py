import sys
from pathlib import Path
from tkinter import Tk
from tkinter.filedialog import askdirectory
import pymmcore
from qtpy.QtCore import QObject, Signal


def find_micromanager():
    if sys.platform == "darwin":
        mm_path = str(next(Path("/Applications/").glob("Micro-Manager*")))
        print(f'Micromanager path: {mm_path}')
        return mm_path

    if sys.platform == "windows":
        Tk().withdraw()
        mm_path = askdirectory(title='Select Micro-Manager directory folder.') # shows dialog box
        print(f'Micromanager path: {mm_path}')
        return mm_path
        
    raise RuntimeError(f"Not configured for OS: {sys.platform}")


class MMCore:
    _instance = None
    # Singleton pattern: https://python-patterns.guide/gang-of-four/singleton/
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = pymmcore.CMMCore(*args, **kwargs)# = to: mmcore = pymmcore.CMMCore()
            cls._instance.setDeviceAdapterSearchPaths([find_micromanager()])# = to: mmcore.setDeviceAdapterSearchPaths([])
        return cls._instance


# class MMCore(QObject):
#     properties_changed = Signal()
#     property_changed = Signal(str, str, object)
#     channel_group_changed = Signal(str)
#     config_group_changed = Signal(str, str)
#     system_configuration_loaded = Signal()
#     pixel_size_changed = Signal(float)
#     pixel_size_affine_changed = Signal(float, float, float, float, float, float)
#     stage_position_changed = Signal(str, float)
#     xy_stage_position_changed = Signal(str, float, float)
#     exposure_changed = Signal(str, float)
#     slm_exposure_changed = Signal(str, float)

#     __instance = None

#     # Singleton pattern: https://python-patterns.guide/gang-of-four/singleton/
#     def __new__(cls) -> pymmcore.CMMCore:
#         if cls.__instance is None:
#             cls.__instance = super().__new__(cls)
#             cls.__instance._initialized = False
#         return cls.__instance

#     def __init__(self, adapter_paths=None):
#         if self._initialized:
#             return
#         super().__init__()
#         self._mmc = pymmcore.CMMCore()
#         if not adapter_paths:
#             adapter_paths = [find_micromanager()]
#         self._mmc.setDeviceAdapterSearchPaths(adapter_paths)
#         self._callback = CallbackRelay(self)
#         self._mmc.registerCallback(self._callback)
#         self._initialized = True

#     def __getattr__(self, name):
#         return getattr(self._mmc, name)

#     def __dir__(self):
#         return set(object.__dir__(self)).union(dir(self._mmc))

#     @property
#     def setProperty(self):
#         # conflicts with QObject.setProperty
#         return self._mmc.setProperty


# class CallbackRelay(pymmcore.MMEventCallback):
#     def __init__(self, emitter):
#         super().__init__()
#         self._emitter = emitter

#     def onPropertiesChanged(self):
#         self._emitter.properties_changed.emit()

#     def onPropertyChanged(self, dev_name: str, prop_name: str, prop_val: str):
#         self._emitter.property_changed.emit(dev_name, prop_name, prop_val)

#     def onChannelGroupChanged(self, new_channel_group_name: str):
#         self._emitter.channel_group_changed.emit(new_channel_group_name)

#     def onConfigGroupChanged(self, group_name: str, new_config_name: str):
#         self._emitter.config_group_changed.emit(group_name, new_config_name)

#     def onSystemConfigurationLoaded(self):
#         self._emitter.system_configuration_loaded.emit()

#     def onPixelSizeChanged(self, new_pixel_size_um: float):
#         self._emitter.pixel_size_changed.emit(new_pixel_size_um)

#     def onPixelSizeAffineChanged(self, v0, v1, v2, v3, v4, v5):
#         self._emitter.pixel_size_affine_changed.emit(v0, v1, v2, v3, v4, v5)

#     def onStagePositionChanged(self, name: str, pos: float):
#         self._emitter.stage_position_changed.emit(name, pos)

#     def onXYStagePositionChanged(self, name: str, xpos: float, ypos: float):
#         self._emitter.xy_stage_position_changed.emit(name, xpos, ypos)

#     def onExposureChanged(self, name: str, new_exposure: float):
#         self._emitter.exposure_changed.emit(name, new_exposure)

#     def onSLMExposureChanged(self, name: str, new_exposure: float):
#         self._emitter.slm_exposure_changed.emit(name, new_exposure)
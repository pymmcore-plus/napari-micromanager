import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pymmcore
from loguru import logger

from ._util import find_micromanager

if TYPE_CHECKING:
    from useq import MDASequence


class MMCorePlus(pymmcore.CMMCore):
    def __init__(self, adapter_paths=None):
        super().__init__()
        self._mm_path = find_micromanager()
        if not adapter_paths:
            adapter_paths = [self._mm_path]
        self.setDeviceAdapterSearchPaths(adapter_paths)
        self._cb = MMCallback(self)
        self.registerCallback(self._cb)

    def setDeviceAdapterSearchPaths(self, adapter_paths):
        # add to PATH as well for dynamic dlls
        env_path = os.environ["PATH"]
        for p in adapter_paths:
            if p not in env_path:
                env_path = p + os.pathsep + env_path
        os.environ["PATH"] = env_path
        logger.info(f"setting adapter search paths: {adapter_paths}")
        super().setDeviceAdapterSearchPaths(adapter_paths)

    def loadSystemConfiguration(self, fileName="demo"):
        if fileName.lower() == "demo":
            fileName = (Path(self._mm_path) / "MMConfig_demo.cfg").resolve()
        super().loadSystemConfiguration(str(fileName))

    def setRelPosition(self, dx=0, dy=0, dz=0) -> None:
        if dx or dy:
            x, y = self.getXPosition(), self.getYPosition()
            self.setXYPosition(x + dx, y + dy)
        if dz:
            z = self.getPosition(self.getFocusDevice())
            self.setZPosition(z + dz)
        self.waitForDevice(self.getXYStageDevice())
        self.waitForDevice(self.getFocusDevice())

    def getZPosition(self) -> float:
        return self.getPosition(self.getFocusDevice())

    def setZPosition(self, val: float) -> None:
        return self.setPosition(self.getFocusDevice(), val)

    def run_mda(self, sequence: "MDASequence") -> None:

        t0 = time.perf_counter()  # reference time, in seconds
        for event in sequence:
            if event.min_start_time:
                elapsed = time.perf_counter() - t0
                if event.min_start_time > elapsed:
                    time.sleep(event.min_start_time - (time.perf_counter() - t0))
            logger.info(event)

            # prep hardware
            if event.x_pos is not None or event.y_pos is not None:
                x = event.x_pos or self.getXPosition()
                y = event.y_pos or self.getYPosition()
                self.setXYPosition(x, y)
            if event.z_pos is not None:
                self.setZPosition(event.z_pos)
            if event.exposure is not None:
                self.setExposure(event.exposure)
            if event.channel is not None:
                self.setConfig(event.channel.group, event.channel.config)

            # acquire
            self.waitForSystem()
            self.snapImage()
            img = self.getImage()

            # emit
            print("send event", img.shape, event)
            # self.mda_frame_ready.emit(img, event)
            print("after send")

        logger.info(f"Finished MDA in {round(time.perf_counter() - t0, 4)} seconds")


class MMCallback(pymmcore.MMEventCallback):
    def __init__(self, core: MMCorePlus):
        super().__init__()
        self._core = core

    def onPropertiesChanged(self):
        _log_callback()

    def onPropertyChanged(self, dev_name: str, prop_name: str, prop_val: str):
        _log_callback()

    def onChannelGroupChanged(self, new_channel_group_name: str):
        _log_callback()

    def onConfigGroupChanged(self, group_name: str, new_config_name: str):
        _log_callback()

    def onSystemConfigurationLoaded(self):
        _log_callback()
        for grp in self._core.getAvailableConfigGroups():
            if grp.lower() == "channel":
                self._core.setChannelGroup(grp)
                break

    def onPixelSizeChanged(self, new_pixel_size_um: float):
        _log_callback()

    def onPixelSizeAffineChanged(self, v0, v1, v2, v3, v4, v5):
        _log_callback()

    def onStagePositionChanged(self, name: str, pos: float):
        _log_callback()

    def onXYStagePositionChanged(self, name: str, xpos: float, ypos: float):
        _log_callback()

    def onExposureChanged(self, name: str, new_exposure: float):
        _log_callback()

    def onSLMExposureChanged(self, name: str, new_exposure: float):
        _log_callback()


def _log_callback():
    frame = sys._getframe().f_back
    name = frame.f_code.co_name.replace("on", "")
    locs = {k: v for k, v in frame.f_locals.items() if k != "self"}
    logger.debug("{}: {}", name, locs)

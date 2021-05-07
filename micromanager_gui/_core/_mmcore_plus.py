import os
import time
from pathlib import Path

import pymmcore
from loguru import logger
from useq import MDASequence

from ._util import find_micromanager


class MMCorePlus(pymmcore.CMMCore):
    def __init__(self, adapter_paths=None):
        super().__init__()
        self._mm_path = find_micromanager()
        if not adapter_paths:
            adapter_paths = [self._mm_path]
        self.setDeviceAdapterSearchPaths(adapter_paths)
        self._callbacks = MMCallback(self)
        self.registerCallback(self._callbacks)
        self._canceled = False
        self._paused = False

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

    def run_mda(self, sequence: MDASequence) -> None:
        self.emit_signal("mda_started")
        self._paused = False
        logger.info("MDA Started: {}", sequence)
        t0 = time.perf_counter()  # reference time, in seconds
        paused_time = 0.0
        for event in sequence:
            while self._paused and not self._canceled:
                paused_time += 0.1  # fixme: be more precise
                time.sleep(0.1)
            if self._canceled:
                logger.warning("MDA Canceled: {}", sequence)
                self.emit_signal("mda_canceled")
                self._canceled = False
                break

            if event.min_start_time:
                go_at = event.min_start_time + paused_time
                # TODO: we need to enter a loop here checking paused and canceled.
                if go_at > time.perf_counter() - t0:
                    time.sleep(go_at - (time.perf_counter() - t0))
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

            self.emit_signal("mda_frame_ready", img, event)
        logger.info("MDA Finished: {}", sequence)
        self.emit_signal("mda_finished")

    def emit_signal(self, signal_name, *args):
        # for pyro subclass
        logger.debug("{}: {}", signal_name, args)

    def cancel(self):
        self._canceled = True

    def toggle_pause(self):
        self._paused = not self._paused
        self.emit_signal("mda_paused", self._paused)


class MMCallback(pymmcore.MMEventCallback):
    def __init__(self, core: MMCorePlus):
        super().__init__()
        self._core = core

    def onPropertiesChanged(self):
        self._core.emit_signal("propertiesChanged")

    def onPropertyChanged(self, dev_name: str, prop_name: str, prop_val: str):
        self._core.emit_signal("propertyChanged", dev_name, prop_name, prop_val)

    def onChannelGroupChanged(self, new_channel_group_name: str):
        self._core.emit_signal("channelGroupChanged", new_channel_group_name)

    def onConfigGroupChanged(self, group_name: str, new_config_name: str):
        self._core.emit_signal("configGroupChanged", group_name, new_config_name)

    def onSystemConfigurationLoaded(self):
        self._core.emit_signal("systemConfigurationLoaded")

    def onPixelSizeChanged(self, new_pixel_size_um: float):
        self._core.emit_signal("pixelSizeChanged", new_pixel_size_um)

    def onPixelSizeAffineChanged(self, v0, v1, v2, v3, v4, v5):
        self._core.emit_signal("pixelSizeAffineChanged", v0, v1, v2, v3, v4, v5)

    def onStagePositionChanged(self, name: str, pos: float):
        self._core.emit_signal("stagePositionChanged", name, pos)

    def onXYStagePositionChanged(self, name: str, xpos: float, ypos: float):
        self._core.emit_signal("xYStagePositionChanged", name, xpos, ypos)

    def onExposureChanged(self, name: str, new_exposure: float):
        self._core.emit_signal("exposureChanged", name, new_exposure)

    def onSLMExposureChanged(self, name: str, new_exposure: float):
        self._core.emit_signal("sLMExposureChanged", name, new_exposure)

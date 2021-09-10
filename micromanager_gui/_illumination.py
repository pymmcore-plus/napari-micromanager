import re

from magicgui import magicgui
from magicgui.widgets import Container
from pymmcore_plus import RemoteMMCore

# LIGHT_LIST = re.compile("(Intensity|Power)s?", re.IGNORECASE)
LIGHT_LIST = re.compile("(Intensity|Power|test)s?", re.IGNORECASE)  # for testing


class Illumination(Container):
    def __init__(self, mmcore: RemoteMMCore):
        super().__init__()

        self._mmc = mmcore

    def make_illumination_magicgui(self):
        c = Container(labels=False)

        devices = self._mmc.getLoadedDevices()
        for i in range(len(devices)):
            device = devices[i]
            properties = self._mmc.getDevicePropertyNames(device)
            for p in range(len(properties)):
                prop = properties[p]
                has_range = self._mmc.hasPropertyLimits(device, prop)
                if LIGHT_LIST.match(prop) and has_range:

                    lower_lim = self._mmc.getPropertyLowerLimit(device, prop)
                    upper_lim = self._mmc.getPropertyUpperLimit(device, prop)
                    is_float = isinstance(upper_lim, float)

                    if is_float:
                        slider_type = "FloatSlider"
                        slider_value = float(self._mmc.getProperty(device, prop))
                    else:
                        slider_type = "Slider"
                        slider_value = self._mmc.getProperty(device, prop)

                    @magicgui(
                        auto_call=True,
                        layout="vertical",
                        dev_name={"bind": device},
                        prop={"bind": prop},
                        slider={
                            "label": f"{device}_{prop}",
                            "widget_type": slider_type,
                            "max": upper_lim,
                            "min": lower_lim,
                        },
                    )
                    def sld(dev_name, prop, slider=slider_value):
                        self._mmc.setProperty(dev_name, prop, slider)

                    c.append(sld)
        c.show()

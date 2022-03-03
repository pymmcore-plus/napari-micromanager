import pytest
from pymmcore_plus import CMMCorePlus, PropertyType

from micromanager_gui._gui_objects._property_widget import PropertyWidget

# not sure how else to parametrize the test without instantiating here at import ...
core = CMMCorePlus.instance()
core.loadSystemConfiguration()
dev_props = [
    (dev, prop)
    for dev in core.getLoadedDevices()
    for prop in core.getDevicePropertyNames(dev)
]


@pytest.mark.parametrize("dev, prop", dev_props)
def test_property_widget(dev, prop, qtbot):
    wdg = PropertyWidget(dev, prop)
    qtbot.addWidget(wdg)
    if prop in ("SimulateCrash", "Trigger"):
        return
    if allowed := core.getAllowedPropertyValues(dev, prop):
        wdg.setValue(allowed[-1])
        val = allowed[-1]
    elif core.getPropertyType(dev, prop) in (PropertyType.Integer, PropertyType.Float):
        # these are just numbers that work for the test config devices
        _vals = {
            "TestProperty": 1,
            "Photon Flux": 50,
            "TestProperty1": 0.01,
            "TestProperty3": 0.002,
            "OnCameraCCDXSize": 20,
            "OnCameraCCDYSize": 20,
            "FractionOfPixelsToDropOrSaturate": 0.05,
        }
        val = _vals.get(prop, 1)

    else:
        val = "some string"
    if not core.isPropertyReadOnly(dev, prop):
        wdg.setValue(val)
        new_val = core.getProperty(dev, prop)
        try:
            assert float(new_val) == float(val)
        except ValueError:
            assert new_val == str(val)

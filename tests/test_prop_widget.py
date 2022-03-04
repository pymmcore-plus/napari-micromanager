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


def assert_equal(a, b):
    try:
        assert float(a) == float(b)
    except ValueError:
        assert str(a) == str(b)


@pytest.mark.parametrize("dev, prop", dev_props)
def test_property_widget(dev, prop, qtbot):
    wdg = PropertyWidget(dev, prop)
    qtbot.addWidget(wdg)
    if core.isPropertyReadOnly(dev, prop) or prop in ("SimulateCrash", "Trigger"):
        return

    start_val = core.getProperty(dev, prop)
    assert_equal(wdg.value(), start_val)

    # make sure that setting the value via the widget updates core
    if allowed := core.getAllowedPropertyValues(dev, prop):
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

    wdg.setValue(val)
    assert_equal(wdg.value(), val)
    assert_equal(core.getProperty(dev, prop), val)

    # make sure that setting value via core updates the widget
    core.setProperty(dev, prop, start_val)
    assert_equal(wdg.value(), start_val)

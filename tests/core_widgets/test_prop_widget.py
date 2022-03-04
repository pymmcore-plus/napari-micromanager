import pytest
from pymmcore_plus import CMMCorePlus, PropertyType

from micromanager_gui._core_widgets import PropertyWidget

# not sure how else to parametrize the test without instantiating here at import ...
CORE = CMMCorePlus()
CORE.loadSystemConfiguration()
dev_props = [
    (dev, prop)
    for dev in CORE.getLoadedDevices()
    for prop in CORE.getDevicePropertyNames(dev)
]


def _assert_equal(a, b):
    try:
        assert float(a) == float(b)
    except ValueError:
        assert str(a) == str(b)


@pytest.mark.parametrize("dev, prop", dev_props)
def test_property_widget(dev, prop, qtbot):
    wdg = PropertyWidget(dev, prop, core=CORE)
    qtbot.addWidget(wdg)
    if CORE.isPropertyReadOnly(dev, prop) or prop in ("SimulateCrash", "Trigger"):
        return

    start_val = CORE.getProperty(dev, prop)
    _assert_equal(wdg.value(), start_val)

    # make sure that setting the value via the widget updates core
    if allowed := CORE.getAllowedPropertyValues(dev, prop):
        val = allowed[-1]
    elif CORE.getPropertyType(dev, prop) in (PropertyType.Integer, PropertyType.Float):
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
    _assert_equal(wdg.value(), val)
    _assert_equal(CORE.getProperty(dev, prop), val)

    # make sure that setting value via core updates the widget
    CORE.setProperty(dev, prop, start_val)
    _assert_equal(wdg.value(), start_val)

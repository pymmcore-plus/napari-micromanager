from pymmcore_plus import CMMCorePlus

from micromanager_gui._gui_objects._device_widget import DeviceWidget, StateDeviceWidget


def test_state_device_widget(qtbot, global_mmcore: CMMCorePlus):
    # FIXME? not sure if possible, but this test won't work for devices that
    # don't broadcast their change with an event from core.
    # for label in global_mmcore.getLoadedDevicesOfType(DeviceType.StateDevice):
    # so, for now, just test objective
    label = "Objective"

    wdg: StateDeviceWidget = DeviceWidget.for_device(label)
    qtbot.addWidget(wdg)
    wdg.show()
    assert wdg.deviceLabel() == label
    assert wdg.deviceName() == "DObjective"
    assert global_mmcore.getStateLabel(label) == wdg._combo.currentText()
    assert global_mmcore.getState(label) == wdg._combo.currentIndex()
    start_state = wdg.state()

    next_state = (wdg.state() + 1) % len(wdg.stateLabels())
    with qtbot.waitSignal(global_mmcore.events.propertyChanged):
        global_mmcore.setState(label, next_state)

    assert wdg.state() != start_state
    assert wdg.data()
    assert wdg.state() == global_mmcore.getState(label) == wdg._combo.currentIndex()
    assert (
        wdg.stateLabel()
        == global_mmcore.getStateLabel(label)
        == wdg._combo.currentText()
    )

    wdg._disconnect()

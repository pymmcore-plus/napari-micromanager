from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from micromanager_gui._core_widgets._stage_widget import StageWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_stage_widget(qtbot: QtBot, global_mmcore: CMMCorePlus):

    # test XY stage
    stage_xy = StageWidget("XY", levels=3)

    qtbot.addWidget(stage_xy)

    assert global_mmcore.getXYStageDevice() == "XY"
    assert stage_xy.radiobutton.isChecked()
    global_mmcore.setProperty("Core", "XYStage", "")
    assert not global_mmcore.getXYStageDevice()
    assert not stage_xy.radiobutton.isChecked()
    stage_xy.radiobutton.setChecked(True)
    assert global_mmcore.getXYStageDevice() == "XY"
    assert stage_xy.radiobutton.isChecked()

    stage_xy._step.setValue(5.0)
    assert stage_xy._step.value() == 5.0
    assert stage_xy._readout.text() == "XY:  -0.0, -0.0"

    x_pos = global_mmcore.getXPosition()
    y_pos = global_mmcore.getYPosition()
    assert x_pos == -0.0
    assert y_pos == -0.0

    xy_up_3 = stage_xy._btns.layout().itemAtPosition(0, 3)
    xy_up_3.widget().click()
    assert (
        (y_pos + (stage_xy._step.value() * 3)) - 1
        < global_mmcore.getYPosition()
        < (y_pos + (stage_xy._step.value() * 3)) + 1
    )
    label_x = round(global_mmcore.getXPosition(), 2)
    label_y = round(global_mmcore.getYPosition(), 2)
    assert stage_xy._readout.text() == f"XY:  {label_x}, {label_y}"

    xy_left_1 = stage_xy._btns.layout().itemAtPosition(3, 2)
    global_mmcore.waitForDevice("XY")
    xy_left_1.widget().click()
    assert (
        (x_pos - stage_xy._step.value()) - 1
        < global_mmcore.getXPosition()
        < (x_pos - stage_xy._step.value()) + 1
    )
    label_x = round(global_mmcore.getXPosition(), 2)
    label_y = round(global_mmcore.getYPosition(), 2)
    assert stage_xy._readout.text() == f"XY:  {label_x}, {label_y}"

    assert stage_xy._readout.text() != "XY:  -0.0, -0.0"
    global_mmcore.waitForDevice("XY")
    global_mmcore.setXYPosition(0.0, 0.0)
    y_pos = global_mmcore.getYPosition()
    x_pos = global_mmcore.getXPosition()
    assert stage_xy._readout.text() == "XY:  -0.0, -0.0"

    stage_xy.snap_checkbox.setChecked(True)
    with qtbot.waitSignal(global_mmcore.events.imageSnapped) as snap:
        global_mmcore.waitForDevice("XY")
        xy_up_3.widget().click()
        assert isinstance(snap.args[0], np.ndarray)

    # test Z stage
    stage_z = StageWidget("Z", levels=3)
    stage_z1 = StageWidget("Z1", levels=3)

    qtbot.addWidget(stage_z)
    qtbot.addWidget(stage_z1)

    assert global_mmcore.getFocusDevice() == "Z"
    assert stage_z.radiobutton.isChecked()
    assert not stage_z1.radiobutton.isChecked()
    global_mmcore.setProperty("Core", "Focus", "Z1")
    assert global_mmcore.getFocusDevice() == "Z1"
    assert not stage_z.radiobutton.isChecked()
    assert stage_z1.radiobutton.isChecked()
    stage_z.radiobutton.setChecked(True)
    assert global_mmcore.getFocusDevice() == "Z"
    assert stage_z.radiobutton.isChecked()
    assert not stage_z1.radiobutton.isChecked()

    stage_z._step.setValue(15.0)
    assert stage_z._step.value() == 15.0
    assert stage_z._readout.text() == "Z:  0.0"

    z_pos = global_mmcore.getPosition()
    assert z_pos == 0.0

    z_up_2 = stage_z._btns.layout().itemAtPosition(1, 3)
    z_up_2.widget().click()
    assert (
        (z_pos + (stage_z._step.value() * 2)) - 1
        < global_mmcore.getPosition()
        < (z_pos + (stage_z._step.value() * 2)) + 1
    )
    assert stage_z._readout.text() == f"Z:  {round(global_mmcore.getPosition(), 2)}"

    global_mmcore.waitForDevice("Z")
    global_mmcore.setPosition(0.0)
    z_pos = global_mmcore.getPosition()
    assert stage_z._readout.text() == "Z:  0.0"

    stage_z.snap_checkbox.setChecked(True)
    with qtbot.waitSignal(global_mmcore.events.imageSnapped) as snap:
        global_mmcore.waitForDevice("Z")
        z_up_2.widget().click()
        assert isinstance(snap.args[0], np.ndarray)

    # disconnect
    assert global_mmcore.getFocusDevice() == "Z"
    assert stage_z.radiobutton.isChecked()
    assert not stage_z1.radiobutton.isChecked()
    stage_z._disconnect()
    stage_z1._disconnect()
    # once disconnected, core changes shouldn't call out to the widget
    global_mmcore.setProperty("Core", "Focus", "Z1")
    assert stage_z.radiobutton.isChecked()
    assert not stage_z1.radiobutton.isChecked()

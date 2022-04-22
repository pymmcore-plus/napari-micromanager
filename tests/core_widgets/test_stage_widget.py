from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from micromanager_gui._core_widgets._stage_widget import StageWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_stage_widget(qtbot: QtBot, global_mmcore: CMMCorePlus):

    stage_xy = StageWidget("XY", levels=3)

    qtbot.addWidget(stage_xy)

    stage_xy._step.setValue(5.0)
    assert stage_xy._step.value() == 5.0
    assert stage_xy._readout.text() == "XY:  -0.0, -0.0"

    y_pos = global_mmcore.getYPosition()
    x_pos = global_mmcore.getXPosition()

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

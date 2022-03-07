from unittest.mock import Mock, call, patch

import pytest
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QDialog

from micromanager_gui._gui_objects._objective_widget import (
    ComboMessageBox,
    MMObjectivesWidget,
)
from micromanager_gui.main_window import MainWindow


def test_crop_camera(main_window: MainWindow):
    assert not main_window.viewer.layers

    cbox = main_window.cam_wdg.cam_roi_combo
    cam_roi_btn = main_window.cam_wdg.crop_btn

    cbox.setCurrentText("1/4")
    cam_roi_btn.click()

    assert len(main_window.viewer.layers) == 1
    assert main_window.viewer.layers[-1].data.shape == (256, 256)
    cbox.setCurrentText("Full")
    assert main_window.viewer.layers[-1].data.shape == (512, 512)
    assert len(main_window.viewer.layers) == 1


def test_objective_widget_changes_objective(global_mmcore: CMMCorePlus, qtbot):
    obj_wdg = MMObjectivesWidget()
    qtbot.addWidget(obj_wdg)

    start_z = 100.0
    global_mmcore.setPosition("Z", start_z)
    stage_mock = Mock()
    obj_wdg._mmc.events.stagePositionChanged.connect(stage_mock)

    assert obj_wdg._combo.currentText() == "Nikon 10X S Fluor"
    with pytest.raises(ValueError):
        obj_wdg._combo.setCurrentText("10asdfdsX")

    assert global_mmcore.getCurrentPixelSizeConfig() == "Res10x"

    new_val = "Nikon 40X Plan Fluor ELWD"
    with qtbot.waitSignal(global_mmcore.events.propertyChanged):
        obj_wdg._combo.setCurrentText(new_val)

    stage_mock.assert_has_calls([call("Z", 0), call("Z", start_z)])
    assert obj_wdg._combo.currentText() == new_val
    assert global_mmcore.getStateLabel(obj_wdg._objective_device) == new_val
    assert global_mmcore.getCurrentPixelSizeConfig() == "Res40x"

    assert global_mmcore.getPosition("Z") == start_z


@patch.object(ComboMessageBox, "exec_")
def test_guess_objectve(dialog_mock, global_mmcore: CMMCorePlus, qtbot):
    dialog_mock.return_value = QDialog.DialogCode.Accepted
    with patch.object(global_mmcore, "guessObjectiveDevices") as mock:
        mock.return_value = ["Objective", "Obj2"]
        obj_wdg = MMObjectivesWidget(mmcore=global_mmcore)
        qtbot.addWidget(obj_wdg)

import pytest
from pymmcore_plus import CMMCorePlus

from micromanager_gui._gui_objects._objective_widget import MMObjectivesWidget
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


def test_objective_widget(global_mmcore: CMMCorePlus, qtbot):

    obj_wdg = MMObjectivesWidget()
    qtbot.addWidget(obj_wdg)

    assert obj_wdg.combo.currentText() == "Nikon 10X S Fluor"
    with pytest.raises(ValueError):
        obj_wdg.combo.setCurrentText("10asdfdsX")

    assert global_mmcore.getCurrentPixelSizeConfig() == "Res10x"

    new_val = "Nikon 40X Plan Flueor ELWD"
    with qtbot.waitSignal(global_mmcore.events.propertyChanged):
        obj_wdg.combo.setCurrentText(new_val)

    assert obj_wdg.combo.currentText() == new_val
    assert global_mmcore.getStateLabel(obj_wdg._objective_device) == new_val
    assert global_mmcore.getCurrentPixelSizeConfig() == "Res40x"

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


def test_objective_device_and_px_size(main_window: MainWindow):
    mmc = main_window._mmc

    main_window.obj_wdg.combo.setCurrentText("10X")
    assert main_window.obj_wdg.combo.currentText() == "10X"
    assert mmc.getCurrentPixelSizeConfig() == "Res10x"
    assert main_window.cam_wdg.px_size_spinbox.value() == 1.0

    main_window.cam_wdg.px_size_spinbox.setValue(6.5)

    mmc.deleteConfigGroup("Objective")
    main_window.obj_wdg._refresh_objective_choices()
    assert main_window.obj_wdg.combo.currentText() == "Nikon 10X S Fluor"
    assert mmc.getCurrentPixelSizeConfig() == "px_size_Nikon 10X S Fluor"

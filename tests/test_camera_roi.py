from micromanager_gui.main_window import MainWindow


def test_crop_camera(main_window: MainWindow):
    pass
    # assert not main_window.viewer.layers

    # cbox = main_window.cam_wdg.cam_roi_combo
    # cam_roi_btn = main_window.cam_wdg.crop_btn

    # cbox.setCurrentText("256 x 256")
    # cam_roi_btn.click()

    # assert len(main_window.viewer.layers) == 1
    # assert main_window.viewer.layers[-1].data.shape == (256, 256)
    # cbox.setCurrentText("Full")
    # assert main_window.viewer.layers[-1].data.shape == (512, 512)
    # assert len(main_window.viewer.layers) == 1

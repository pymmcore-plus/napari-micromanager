from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from useq import MDASequence

    from micromanager_gui.main_window import MainWindow


def test_explorer_main(main_window: MainWindow, qtbot: QtBot):

    mmc = main_window._mmc
    mmc.setXYPosition(0.0, 0.0)
    mmc.setPosition(0.0)

    mmc.setConfig(
        "Objective", "10X"
    )  # this it is also setting mmc.setPixelSizeConfig('Res10x')

    explorer = main_window.explorer
    explorer.scan_size_spinBox_r.setValue(2)
    explorer.scan_size_spinBox_c.setValue(2)
    explorer.ovelap_spinBox.setValue(0)
    explorer.add_ch_explorer_Button.click()
    explorer.grid_checkbox.setChecked(True)

    assert not main_window.viewer.layers

    sequence = None

    @mmc.mda.events.sequenceStarted.connect
    def get_seq(seq: MDASequence):
        nonlocal sequence
        sequence = seq

    with qtbot.waitSignals(
        [mmc.mda.events.sequenceStarted, mmc.mda.events.sequenceFinished], timeout=7500
    ):
        explorer.start_scan_Button.click()

        meta = main_window._mda_meta

    # wait to finish returning to start pos
    mmc.waitForSystem()
    assert main_window.explorer._set_grid() == [
        ("Grid_001_Pos000", -512.005, 512.005, 0.0),
        ("Grid_001_Pos001", -0.0049999999999954525, 512.005, 0.0),
        ("Grid_001_Pos002", -0.0049999999999954525, 0.0049999999999954525, 0.0),
        ("Grid_001_Pos003", -512.005, 0.0049999999999954525, 0.0),
    ]

    assert mmc.getPixelSizeUm() == 1
    assert mmc.getROI(mmc.getCameraDevice())[-1] == 512
    assert mmc.getROI(mmc.getCameraDevice())[-2] == 512

    assert meta
    assert meta.mode == "explorer"

    assert meta.explorer_translation_points == [
        (-256.0, 256.0, 0, 0),
        (256.0, 256.0, 0, 1),
        (256.0, -256.0, 1, 0),
        (-256.0, -256.0, 1, 1),
    ]

    assert main_window.viewer.layers[-1].data.shape == (1, 512, 512)
    assert len(main_window.viewer.layers) == 4

    _layer = main_window.viewer.layers[-1]
    assert _layer.metadata["uid"] == sequence.uid
    assert _layer.metadata["grid"] == "001"
    assert _layer.metadata["grid_pos"] == "Pos003"
    assert _layer.metadata["translate"]
    assert _layer.metadata["pos"] == (-256.0, -256.0, 0.0)

    # checking the linking  of the layers
    assert len(main_window.viewer.layers) == 4
    layer_0 = main_window.viewer.layers[0]
    layer_0.visible = False

    # check that also the last layer is not visible
    layer_1 = main_window.viewer.layers[1]
    assert not layer_1.visible


# def test_saving_explorer(main_window: MainWindow, qtbot: QtBot):

#     mmc = main_window._mmc

#     explorer = main_window.explorer
#     explorer.scan_size_spinBox_r.setValue(2)
#     explorer.scan_size_spinBox_c.setValue(2)
#     explorer.ovelap_spinBox.setValue(0)
#     explorer.add_ch_explorer_Button.click()
#     explorer.channel_explorer_comboBox.setCurrentText("Cy5")
#     explorer.add_ch_explorer_Button.click()
#     explorer.channel_explorer_comboBox.setCurrentText("FITC")

#     explorer.save_explorer_groupBox.setChecked(False)

#     sequence = None

#     @mmc.mda.events.sequenceStarted.connect
#     def get_seq(seq: MDASequence):
#         nonlocal sequence
#         sequence = seq

#     with tempfile.TemporaryDirectory() as td:
#         tmp_path = Path(td)

#         with qtbot.waitSignals(
#             [mmc.mda.events.sequenceStarted, mmc.mda.events.sequenceFinished]
#         ):
#             explorer.start_scan_Button.click()
#             meta = main_window._mda_meta

#         layer_list = list(main_window.viewer.layers)
#         assert len(layer_list) == 4

#         _layer = main_window.viewer.layers[0]
#         assert _layer.data.shape == (2, 512, 512)
#         assert _layer.metadata["uid"] == sequence.uid

#         meta.save_dir = str(tmp_path)
#         meta.should_save = True

# NEED TO FIX save_sequence
# save_sequence(sequence, layer_list, meta)

# folder = tmp_path / "scan_Experiment_000"  # after _imsave()

# file_list = sorted(pth.name for pth in folder.iterdir())

# print(file_list)
# assert file_list == ["Cy5.tif", "FITC.tif"]

# saved_file = tifffile.imread(folder / "Cy5.tif")
# assert saved_file.shape == (4, 512, 512)

# saved_file = tifffile.imread(folder / "FITC")

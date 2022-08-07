from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import tifffile

from micromanager_gui import _mda
from micromanager_gui._saving import save_sequence

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from useq import MDASequence

    from micromanager_gui.main_window import MainWindow


def test_explorer(main_window: MainWindow, qtbot: QtBot):

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

    assert not main_window.viewer.layers

    # grab these in callback so we get the real meta that is
    # created once we start the scan
    sequence = None
    meta = None

    @mmc.mda.events.sequenceStarted.connect
    def get_seq(seq: MDASequence):
        nonlocal sequence, meta
        sequence = seq
        meta = _mda.SEQUENCE_META[seq]

    with qtbot.waitSignals(
        [mmc.mda.events.sequenceStarted, mmc.mda.events.sequenceFinished], timeout=7500
    ):
        explorer.start_scan()

    # wait to finish returning to start pos
    mmc.waitForSystem()
    assert main_window.explorer.set_grid() == [
        (-256.0, 256.0, 0.0),
        (256.0, 256.0, 0.0),
        (256.0, -256.0, 0.0),
        (-256.0, -256.0, 0.0),
    ]
    assert mmc.getPixelSizeUm() == 1
    assert mmc.getROI(mmc.getCameraDevice())[-1] == 512
    assert mmc.getROI(mmc.getCameraDevice())[-2] == 512

    assert meta
    assert meta.mode == "explorer"

    assert main_window.viewer.layers[-1].data.shape == (512, 512)
    assert len(main_window.viewer.layers) == 4

    _layer = main_window.viewer.layers[-1]
    assert _layer.metadata["ch_name"] == "Cy5"
    assert _layer.metadata["ch_id"] == 0
    assert _layer.metadata["uid"] == sequence.uid

    # checking the linking  of the layers
    assert len(main_window.viewer.layers) == 4
    layer_0 = main_window.viewer.layers[0]
    layer_0.visible = False

    # check that also the last layer is not visible
    layer_1 = main_window.viewer.layers[1]
    assert not layer_1.visible


def test_saving_explorer(main_window: MainWindow, qtbot: QtBot):

    mmc = main_window._mmc
    # grab these in callback so we get the real meta that is
    # created once we start the scan
    sequence = None
    meta = None

    explorer = main_window.explorer
    explorer.scan_size_spinBox_r.setValue(2)
    explorer.scan_size_spinBox_c.setValue(2)
    explorer.ovelap_spinBox.setValue(0)
    explorer.add_ch_explorer_Button.click()
    explorer.channel_explorer_comboBox.setCurrentText("Cy5")
    explorer.add_ch_explorer_Button.click()
    explorer.channel_explorer_comboBox.setCurrentText("FITC")

    @mmc.mda.events.sequenceStarted.connect
    def get_seq(seq: MDASequence):
        nonlocal sequence, meta
        sequence = seq
        meta = _mda.SEQUENCE_META[seq]

    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        explorer.dir_explorer_lineEdit.setText(str(tmp_path))
        explorer.save_explorer_groupBox.setChecked(True)

        with qtbot.waitSignals(
            [mmc.mda.events.sequenceStarted, mmc.mda.events.sequenceFinished]
        ):
            explorer.start_scan_Button.click()

        layer_list = list(main_window.viewer.layers)
        assert len(layer_list) == 8

        save_sequence(sequence, layer_list, meta)

        folder = tmp_path / "scan_Experiment_000"  # after _imsave()

        file_list = sorted(pth.name for pth in folder.iterdir())
        assert file_list == ["Cy5.tif", "FITC.tif"]

        saved_file = tifffile.imread(folder / "Cy5.tif")
        assert saved_file.shape == (4, 512, 512)

        saved_file = tifffile.imread(folder / "FITC.tif")
        assert saved_file.shape == (4, 512, 512)

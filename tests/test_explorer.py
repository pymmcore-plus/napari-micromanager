from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import tifffile

from micromanager_gui import _mda
from micromanager_gui._saving import save_sequence

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from useq import MDASequence

    from micromanager_gui._gui_objects._sample_explorer_widget._sample_explorer_widget import (  # noqa: E501
        MMExploreSample,
    )
    from micromanager_gui.main_window import MainWindow

    ExplorerTuple = Tuple[MainWindow, MMExploreSample]


def test_explorer(explorer_two_channels: ExplorerTuple, qtbot: QtBot):

    main_win, explorer = explorer_two_channels

    mmc = main_win._mmc

    mmc.setConfig(
        "Objective", "10X"
    )  # this it is also setting mmc.setPixelSizeConfig('Res10x')

    assert main_win.explorer.set_grid() == [
        ("Grid_001_Pos000", -256.0, 256.0, 0.0),
        ("Grid_001_Pos001", 256.0, 256.0, 0.0),
        ("Grid_001_Pos002", 256.0, -256.0, 0.0),
        ("Grid_001_Pos003", -256.0, -256.0, 0.0),
        ("Grid_002_Pos000", -256.0, 256.0, 0.0),
        ("Grid_002_Pos001", 256.0, 256.0, 0.0),
        ("Grid_002_Pos002", 256.0, -256.0, 0.0),
        ("Grid_002_Pos003", -256.0, -256.0, 0.0),
    ]

    assert not main_win.viewer.layers

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

    assert mmc.getPixelSizeUm() == 1
    assert mmc.getROI(mmc.getCameraDevice())[-1] == 512
    assert mmc.getROI(mmc.getCameraDevice())[-2] == 512

    assert meta
    assert meta.mode == "explorer"

    assert len(main_win.viewer.layers) == 8
    for layer in main_win.viewer.layers:
        assert layer.data.shape == (3, 2, 512, 512)
        # assert layer.data.shape == (2, 3, 1, 512, 512)

    _layer_1 = main_win.viewer.layers[0]
    assert _layer_1.metadata["uid"] == sequence.uid
    assert _layer_1.metadata["grid"] == "001"
    assert _layer_1.metadata["grid_pos"] == "Pos000"

    _layer_8 = main_win.viewer.layers[-1]
    assert _layer_8.metadata["uid"] == sequence.uid
    assert _layer_8.metadata["grid"] == "002"
    assert _layer_8.metadata["grid_pos"] == "Pos003"

    # checking the linking  of the layers
    assert len(main_win.viewer.layers) == 8
    layer_0 = main_win.viewer.layers[0]
    layer_0.visible = False

    layer_8 = main_win.viewer.layers[-1]
    layer_8.visible = False

    # check that also the last layer is not visible
    layer_1 = main_win.viewer.layers[1]
    layer_7 = main_win.viewer.layers[-2]
    assert not layer_1.visible
    assert not layer_7.visible


def test_saving_explorer(qtbot: QtBot, explorer_two_channels: ExplorerTuple):

    main_win, explorer = explorer_two_channels
    mmc = main_win._mmc
    # grab these in callback so we get the real meta that is
    # created once we start the scan
    sequence = None
    meta = None

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
            explorer.start_scan()

        layer_list = list(main_win.viewer.layers)
        assert len(layer_list) == 8
        for layer in main_win.viewer.layers:
            assert layer.data.shape == (3, 2, 512, 512)
            # assert layer.data.shape == (2, 3, 1, 512, 512)

        save_sequence(sequence, layer_list, meta)

        main_folder = tmp_path / f"{meta.file_name}_000"  # after _imsave()

        file_list = sorted(pth.name for pth in main_folder.iterdir())
        assert file_list == [f"{meta.file_name}_Grid_001", f"{meta.file_name}_Grid_002"]

        grid_subfolder_1 = main_folder / f"{meta.file_name}_Grid_001"
        filename_list = sorted(file.name for file in grid_subfolder_1.iterdir())
        for idx, fname in enumerate(filename_list):
            assert fname == f"{meta.file_name}_Grid_001_Pos{idx:03d}.tif"

        saved_file = tifffile.imread(
            grid_subfolder_1 / f"{meta.file_name}_Grid_001_Pos000.tif"
        )
        assert saved_file.shape == (3, 2, 512, 512)
        # assert saved_file.shape == (2, 3, 1, 512, 512)

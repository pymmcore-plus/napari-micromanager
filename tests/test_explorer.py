from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import numpy as np
import tifffile

from micromanager_gui._saving import save_sequence

if TYPE_CHECKING:
    from useq import MDASequence

    from micromanager_gui.main_window import MainWindow
    from micromanager_gui.multid_widget import SequenceMeta

    ExplorerTuple = Tuple[MainWindow, MDASequence, SequenceMeta]


def test_explorer(explorer_no_channel: ExplorerTuple):

    main_win, sequence, meta = explorer_no_channel

    mmc = main_win._mmc
    mmc.setXYPosition(0.0, 0.0)
    mmc.setPosition(0.0)

    mmc.setConfig(
        "Objective", "10X"
    )  # this it is also setting mmc.setPixelSizeConfig('Res10x')

    main_win.explorer.pixel_size = mmc.getPixelSizeUm()

    assert mmc.getPixelSizeUm() == 1
    assert mmc.getROI(mmc.getCameraDevice())[-1] == 512
    assert mmc.getROI(mmc.getCameraDevice())[-2] == 512

    assert main_win.explorer.set_grid() == [
        [-256.0, 256.0, 0.0],
        [256.0, 256.0, 0.0],
        [256.0, -256.0, 0.0],
        [-256.0, -256.0, 0.0],
    ]

    assert not main_win.viewer.layers
    assert meta.mode == "explorer"

    for event in sequence:
        frame = np.random.rand(512, 512)
        main_win.explorer._on_explorer_frame(frame, event)

    assert main_win.viewer.layers[-1].data.shape == (512, 512)
    assert len(main_win.viewer.layers) == 4

    _layer = main_win.viewer.layers[-1]
    assert _layer.metadata["ch_name"] == "FITC"
    assert _layer.metadata["ch_id"] == 0
    assert _layer.metadata["uid"] == sequence.uid


def test_explorer_link_layer(explorer_one_channel: ExplorerTuple):

    main_win, sequence, _ = explorer_one_channel

    assert len(main_win.viewer.layers) == 4

    for _layer in main_win.viewer.layers:
        assert _layer.metadata["uid"] == sequence.uid
        assert _layer.metadata["ch_name"] == "FITC"
        assert _layer.metadata["ch_id"] == 0

    main_win.explorer._on_mda_finished(sequence)

    # hide first layer
    layer_0 = main_win.viewer.layers[0]
    layer_0.visible = False

    # check that also the last layer is not visible
    layer_1 = main_win.viewer.layers[1]
    assert not layer_1.visible


def test_saving_explorer(qtbot, explorer_two_channel: ExplorerTuple):

    main_win, sequence, meta = explorer_two_channel

    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)

        meta.should_save = True
        meta.save_dir = tmp_path

        main_win.viewer.add_image(np.random.rand(10, 10), name="preview")

        layer_list = [lay for lay in main_win.viewer.layers]
        assert len(layer_list) == 9

        save_sequence(sequence, layer_list, meta)

        folder = tmp_path / "scan_EXPLORER_000"  # after _imsave()

        file_list = sorted(pth.name for pth in folder.iterdir())
        assert file_list == ["Cy5.tif", "FITC.tif"]

        saved_file = tifffile.imread(folder / "Cy5.tif")
        assert saved_file.shape == (4, 10, 10)

        saved_file = tifffile.imread(folder / "FITC.tif")
        assert saved_file.shape == (4, 10, 10)

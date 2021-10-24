import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import tifffile

from micromanager_gui._saving import save_sequence

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_explorer(setup_explorer):

    main_win = setup_explorer[0]
    explorer = setup_explorer[1]
    meta = setup_explorer[2]
    seq = setup_explorer[3]

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

    for event in explorer:
        frame = np.random.rand(512, 512)
        main_win.explorer._on_explorer_frame(frame, event)

    assert main_win.viewer.layers[-1].data.shape == (512, 512)
    assert len(main_win.viewer.layers) == 4

    _layer = main_win.viewer.layers[-1]
    assert _layer.metadata["ch_name"] == "FITC"
    assert _layer.metadata["ch_id"] == 0
    assert seq == _layer.metadata["uid"]


def test_explorer_link_layer(setup_explorer_one_channel):

    main_win = setup_explorer_one_channel[0]
    explorer = setup_explorer_one_channel[1]
    seq = setup_explorer_one_channel[3]

    assert len(main_win.viewer.layers) == 4

    for _layer in main_win.viewer.layers:
        assert _layer.metadata["uid"] == seq
        assert _layer.metadata["ch_name"] == "FITC"
        assert _layer.metadata["ch_id"] == 0

    main_win.explorer._on_mda_finished(explorer)

    # hide first layer
    layer_0 = main_win.viewer.layers[0]
    layer_0.visible = False

    # check that also the last layer is not visible
    layer_1 = main_win.viewer.layers[1]
    assert not layer_1.visible


def test_saving_explorer(qtbot: "QtBot", setup_explorer_two_channel):
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)

        main_win = setup_explorer_two_channel[0]
        explorer = setup_explorer_two_channel[1]
        meta = setup_explorer_two_channel[2]

        meta.should_save = True
        meta.save_dir = tmp_path

        main_win.viewer.add_image(np.random.rand(10, 10), name="preview")

        layer_list = [lay for lay in main_win.viewer.layers]
        assert len(layer_list) == 9

        save_sequence(explorer, layer_list, meta)

        folder = tmp_path / "scan_EXPLORER_000"  # after _imsave()

        file_list = sorted(pth.name for pth in folder.iterdir())
        assert file_list == ["Cy5.tif", "FITC.tif"]

        saved_file = tifffile.imread(folder / "Cy5.tif")
        assert saved_file.shape == (4, 10, 10)

        saved_file = tifffile.imread(folder / "FITC.tif")
        assert saved_file.shape == (4, 10, 10)

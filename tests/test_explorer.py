import os
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
import tifffile
from napari import Viewer
from pymmcore_plus import server
from useq import MDASequence

from micromanager_gui._saving import save_sequence
from micromanager_gui.main_window import MainWindow
from micromanager_gui.multid_widget import SequenceMeta

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture(params=["local", "remote"])
def main_window(qtbot, request):
    if request.param == "remote":
        server.try_kill_server()

    viewer = Viewer(show=False)
    win = MainWindow(viewer=viewer, remote=request.param == "remote")
    config_path = os.path.dirname(os.path.abspath(__file__)) + "/test_config.cfg"
    win._mmc.loadSystemConfiguration(config_path)

    try:
        yield win
    finally:
        viewer.close()


@pytest.fixture
def setup_explorer(main_window: MainWindow):

    main_window.explorer.scan_size_spinBox_r.setValue(2)
    main_window.explorer.scan_size_spinBox_c.setValue(2)
    main_window.explorer.ovelap_spinBox.setValue(0)

    explorer = MDASequence(
        channels=["FITC"],
        stage_positions=[
            {"x": -256.0, "y": 256.0, "z": 0.0},
            {"x": 256.0, "y": 256.0, "z": 0.0},
            {"x": 256.0, "y": -256.0, "z": 0.0},
            {"x": -256.0, "y": -256.0, "z": 0.0},
        ],
        uid=uuid.uuid4(),
    )

    # main_window.explorer.SEQUENCE_META[explorer] = SequenceMeta(mode="explorer")
    main_window.explorer.SEQUENCE_META[explorer] = SequenceMeta(
        mode="explorer",
        split_channels=True,
        should_save=False,
        file_name="EXPLORER",
        save_dir="",
    )
    meta = main_window.explorer.SEQUENCE_META[explorer]
    seq = explorer.uid

    return main_window, explorer, meta, seq


@pytest.fixture
def setup_explorer_one_channel(setup_explorer):

    main_win = setup_explorer[0]
    seq = setup_explorer[3]

    for i in range(4):
        layer = main_win.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i}_[FITC_idx0]"
        )
        layer.metadata["uid"] = seq
        layer.metadata["ch_name"] = "FITC"
        layer.metadata["ch_id"] = 0

    return setup_explorer


@pytest.fixture
def setup_explorer_two_channel(setup_explorer):

    main_win = setup_explorer[0]
    seq = setup_explorer[3]

    for i in range(4):
        layer_1 = main_win.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i:03}_[FITC_idx0]"
        )
        layer_1.metadata["uid"] = seq
        layer_1.metadata["ch_name"] = "FITC"
        layer_1.metadata["ch_id"] = 0
        layer_1.metadata["scan_position"] = f"Pos{i:03}"

        layer_2 = main_win.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i:03}_[Cy5_idx0]"
        )
        layer_2.metadata["uid"] = seq
        layer_2.metadata["ch_name"] = "Cy5"
        layer_2.metadata["ch_id"] = 1
        layer_2.metadata["scan_position"] = f"Pos{i:03}"

    return setup_explorer


# def add_two_channels(main_window: MainWindow):

#     for i in range(4):
#         layer = main_window.viewer.add_image(
#             np.random.rand(10, 10), name=f"Pos{i}_[FITC_idx0]"
#         )
#         layer.metadata["uid"] = seq_uid
#         layer.metadata["ch_name"] = "FITC"
#         layer.metadata["ch_id"] = 0


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

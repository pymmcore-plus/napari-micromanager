import os
import uuid
from typing import TYPE_CHECKING

import numpy as np
import pytest
from napari import Viewer
from pymmcore_plus import server
from useq import MDASequence

from micromanager_gui.main_window import MainWindow
from micromanager_gui.multid_widget import SequenceMeta

if TYPE_CHECKING:
    pass


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


def test_explorer(main_window: MainWindow):

    mmc = main_window._mmc

    mmc.setXYPosition(0.0, 0.0)
    mmc.setPosition(0.0)

    main_window.explorer.scan_size_spinBox_r.setValue(2)
    main_window.explorer.scan_size_spinBox_c.setValue(2)
    main_window.explorer.ovelap_spinBox.setValue(0)

    mmc.setConfig(
        "Objective", "10X"
    )  # this it is also setting mmc.setPixelSizeConfig('Res10x')

    main_window.explorer.pixel_size = mmc.getPixelSizeUm()

    assert mmc.getPixelSizeUm() == 1
    assert mmc.getROI(mmc.getCameraDevice())[-1] == 512
    assert mmc.getROI(mmc.getCameraDevice())[-2] == 512

    assert main_window.explorer.set_grid() == [
        [-256.0, 256.0, 0.0],
        [256.0, 256.0, 0.0],
        [256.0, -256.0, 0.0],
        [-256.0, -256.0, 0.0],
    ]

    assert not main_window.viewer.layers

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

    main_window.explorer.SEQUENCE_META[explorer] = SequenceMeta(mode="explorer")
    meta = main_window.explorer.SEQUENCE_META[explorer]
    seq = explorer.uid

    assert meta.mode == "explorer"

    for event in explorer:
        frame = np.random.rand(512, 512)
        main_window.explorer._on_explorer_frame(frame, event)

    assert main_window.viewer.layers[-1].data.shape == (512, 512)
    assert len(main_window.viewer.layers) == 4

    _layer = main_window.viewer.layers[-1]
    assert _layer.metadata["ch_name"] == "FITC"
    assert _layer.metadata["ch_id"] == 0
    assert seq == _layer.metadata["uid"]


def test_explorer_link_layer(main_window: MainWindow):

    explorer = MDASequence(
        uid=uuid.uuid4(),
    )

    main_window.explorer.SEQUENCE_META[explorer] = SequenceMeta(mode="explorer")
    seq_uid = explorer.uid

    for i in range(4):
        layer = main_window.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i}_[FITC_idx0]"
        )
        layer.metadata["uid"] = seq_uid
        layer.metadata["ch_name"] = "FITC"
        layer.metadata["ch_id"] = 0

    assert len(main_window.viewer.layers) == 4

    for _layer in main_window.viewer.layers:
        assert _layer.metadata["uid"] == seq_uid
        assert _layer.metadata["ch_name"] == "FITC"
        assert _layer.metadata["ch_id"] == 0

    main_window.explorer._on_mda_finished(explorer)

    # hide first layer
    layer_0 = main_window.viewer.layers[0]
    layer_0.visible = False

    # check that also the last layer is not visible
    layer_1 = main_window.viewer.layers[1]
    assert not layer_1.visible

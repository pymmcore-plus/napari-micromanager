import os
import uuid

import numpy as np
import pytest
from napari import Viewer
from pymmcore_plus import server
from useq import MDASequence

from micromanager_gui.main_window import MainWindow
from micromanager_gui.multid_widget import SequenceMeta


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
def setup_explorer_no_channel(main_window: MainWindow):

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
def setup_explorer_one_channel(setup_explorer_no_channel):

    main_win = setup_explorer_no_channel[0]
    seq = setup_explorer_no_channel[3]

    for i in range(4):
        layer = main_win.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i}_[FITC_idx0]"
        )
        layer.metadata["uid"] = seq
        layer.metadata["ch_name"] = "FITC"
        layer.metadata["ch_id"] = 0

    return setup_explorer_no_channel


@pytest.fixture
def setup_explorer_two_channel(setup_explorer_no_channel):

    main_win = setup_explorer_no_channel[0]
    seq = setup_explorer_no_channel[3]

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

    return setup_explorer_no_channel

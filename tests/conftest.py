import os
import uuid
from typing import Tuple

import numpy as np
import pytest
from pymmcore_plus import CMMCorePlus
from useq import MDASequence

from micromanager_gui import _core
from micromanager_gui.main_window import MainWindow
from micromanager_gui.multid_widget import SequenceMeta

ExplorerTuple = Tuple[MainWindow, MDASequence, SequenceMeta]


@pytest.fixture(params=["local"])
def global_mmcore(request):
    _core._SESSION_CORE = CMMCorePlus()  # refresh singleton
    if request.param == "remote":
        from pymmcore_plus import server

        server.try_kill_server()

    mmc = _core.get_core_singleton(remote=request.param == "remote")
    if len(mmc.getLoadedDevices()) < 2:
        mmc.loadSystemConfiguration()
    return mmc


@pytest.fixture
def main_window(global_mmcore, make_napari_viewer):
    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer)
    config_path = os.path.dirname(os.path.abspath(__file__)) + "/test_config.cfg"
    win.cfg_wdg.cfg_LineEdit.setText(config_path)
    win._mmc.loadSystemConfiguration(config_path)
    return win


@pytest.fixture
def explorer_no_channel(main_window: MainWindow) -> ExplorerTuple:

    main_window.explorer.scan_size_spinBox_r.setValue(2)
    main_window.explorer.scan_size_spinBox_c.setValue(2)
    main_window.explorer.ovelap_spinBox.setValue(0)

    sequence = MDASequence(
        channels=["FITC"],
        stage_positions=[
            {"x": -256.0, "y": 256.0, "z": 0.0},
            {"x": 256.0, "y": 256.0, "z": 0.0},
            {"x": 256.0, "y": -256.0, "z": 0.0},
            {"x": -256.0, "y": -256.0, "z": 0.0},
        ],
        uid=uuid.uuid4(),
    )

    main_window.explorer.SEQUENCE_META[sequence] = SequenceMeta(
        mode="explorer",
        split_channels=True,
        should_save=False,
        file_name="EXPLORER",
        save_dir="",
    )
    meta = main_window.explorer.SEQUENCE_META[sequence]

    return main_window, sequence, meta


@pytest.fixture
def explorer_one_channel(explorer_no_channel: ExplorerTuple) -> ExplorerTuple:

    main_win, sequence, _ = explorer_no_channel

    for i in range(4):
        layer = main_win.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i}_[FITC_idx0]"
        )
        layer.metadata["uid"] = sequence.uid
        layer.metadata["ch_name"] = "FITC"
        layer.metadata["ch_id"] = 0

    return explorer_no_channel


@pytest.fixture
def explorer_two_channel(explorer_no_channel: ExplorerTuple) -> ExplorerTuple:

    main_win, sequence, _ = explorer_no_channel

    for i in range(4):
        layer_1 = main_win.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i:03}_[FITC_idx0]"
        )
        layer_1.metadata["uid"] = sequence.uid
        layer_1.metadata["ch_name"] = "FITC"
        layer_1.metadata["ch_id"] = 0
        layer_1.metadata["scan_position"] = f"Pos{i:03}"

        layer_2 = main_win.viewer.add_image(
            np.random.rand(10, 10), name=f"Pos{i:03}_[Cy5_idx0]"
        )
        layer_2.metadata["uid"] = sequence.uid
        layer_2.metadata["ch_name"] = "Cy5"
        layer_2.metadata["ch_id"] = 1
        layer_2.metadata["scan_position"] = f"Pos{i:03}"

    return explorer_no_channel

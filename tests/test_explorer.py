from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from napari_micromanager._gui_objects._sample_explorer_widget import SampleExplorer
from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from pymmcore_plus.mda import MDAEngine

if TYPE_CHECKING:
    from napari_micromanager.main_window import MainWindow
    from pytestqt.qtbot import QtBot
    from useq import MDASequence


def test_explorer_main(main_window: MainWindow, qtbot: QtBot):

    mmc = main_window._mmc
    mmc.setXYPosition(0.0, 0.0)
    mmc.setPosition(0.0)

    mmc.setConfig(
        "Objective", "10X"
    )  # this it is also setting mmc.setPixelSizeConfig('Res10x')

    main_window._show_dock_widget("Explorer")
    explorer = main_window._dock_widgets["Explorer"].widget()
    assert isinstance(explorer, SampleExplorer)
    explorer.grid_params.scan_size_spinBox_r.setValue(2)
    explorer.grid_params.scan_size_spinBox_c.setValue(2)
    explorer.grid_params.overlap_spinBox.setValue(0)
    # FIXME! napari-micromanager should be using things like `set_state` ...
    # not accessing and clicking individual widgets
    explorer.channel_groupbox._add_button.click()
    explorer.radiobtn_grid.setChecked(True)

    assert not main_window.viewer.layers

    assert explorer._create_grid_coords() == [
        {
            "x": -256.0,
            "y": 256.0,
            "z": 0.0,
            "name": "Grid001_Pos000",
            "z_plan": {"go_up": True},
        },
        {
            "x": 256.0,
            "y": 256.0,
            "z": 0.0,
            "name": "Grid001_Pos001",
            "z_plan": {"go_up": True},
        },
        {
            "x": 256.0,
            "y": -256.0,
            "z": 0.0,
            "name": "Grid001_Pos002",
            "z_plan": {"go_up": True},
        },
        {
            "x": -256.0,
            "y": -256.0,
            "z": 0.0,
            "name": "Grid001_Pos003",
            "z_plan": {"go_up": True},
        },
    ]

    uid = None
    meta = None

    @mmc.mda.events.sequenceStarted.connect
    def get_seq(seq: MDASequence):
        nonlocal uid, meta
        meta = seq.metadata[SEQUENCE_META_KEY]
        uid = seq.uid

    with qtbot.waitSignals(
        [mmc.mda.events.sequenceStarted, mmc.mda.events.sequenceFinished], timeout=7500
    ):
        explorer.buttons_wdg.run_button.click()

    # wait to finish returning to start pos
    mmc.waitForSystem()

    assert mmc.getPixelSizeUm() == 1
    assert mmc.getROI(mmc.getCameraDevice())[-1] == 512
    assert mmc.getROI(mmc.getCameraDevice())[-2] == 512

    assert isinstance(meta, SequenceMeta)
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
    assert _layer.metadata["uid"] == uid
    assert _layer.metadata["grid"] == "Grid001"
    assert _layer.metadata["grid_pos"] == "Pos003"
    assert _layer.metadata["translate"]

    # checking the linking  of the layers
    assert len(main_window.viewer.layers) == 4
    layer_0 = main_window.viewer.layers[0]
    layer_0.visible = False

    # check that also the last layer is not visible
    layer_1 = main_window.viewer.layers[1]
    assert not layer_1.visible


@pytest.mark.parametrize("Z", ["", "withZ"])
@pytest.mark.parametrize("C", ["", "withC"])
@pytest.mark.parametrize("T", ["", "withT"])
@pytest.mark.parametrize("Tr", ["", "withTranslate"])
def test_saving_explorer(
    qtbot: QtBot, main_window: MainWindow, T, C, Z, Tr, tmp_path: Path
):

    NAME = "test_explorer"
    main_window._show_dock_widget("Explorer")
    _exp = cast(SampleExplorer, main_window._dock_widgets["Explorer"].widget())
    assert isinstance(_exp, SampleExplorer)
    _exp._save_groupbox.setChecked(True)
    _exp._save_groupbox._directory.setText(str(tmp_path))
    _exp._save_groupbox._fname.setText(NAME)

    _exp.grid_params.scan_size_spinBox_r.setValue(2)
    _exp.grid_params.scan_size_spinBox_c.setValue(1)
    _exp.grid_params.overlap_spinBox.setValue(0)

    _exp.time_groupbox.setChecked(bool(T))
    _exp.time_groupbox.set_state({"interval": timedelta(seconds=0.250), "loops": 3})

    _exp.stack_groupbox.setChecked(bool(Z))
    _exp.stack_groupbox._zmode_tabs.setCurrentIndex(1)
    z_range_wdg = _exp.stack_groupbox._zmode_tabs.widget(1)
    z_range_wdg._zrange_spinbox.setValue(3)
    _exp.stack_groupbox._zstep_spinbox.setValue(1)

    # 2 Channels
    state = [{"config": "DAPI", "exposure": 5.0}]
    if C:
        state.append({"config": "Cy5", "exposure": 5.0})
    _exp.channel_groupbox.set_state(state)

    if Tr:
        _exp.radiobtn_grid.setChecked(True)
        _exp.radiobtn_multid_stack.setChecked(False)
    else:
        _exp.radiobtn_grid.setChecked(False)
        _exp.radiobtn_multid_stack.setChecked(True)

    exp_seq: MDASequence = None

    mmc = main_window._mmc
    # re-register twice to fully exercise the logic of the update
    # functions - the initial connections are made in init
    # then after that they are fully handled by the _update_mda_engine
    # callbacks
    mmc.register_mda_engine(MDAEngine(mmc))
    mmc.register_mda_engine(MDAEngine(mmc))

    @mmc.mda.events.sequenceStarted.connect
    def _store_mda(_seq):
        nonlocal exp_seq
        exp_seq = _seq

    # make the images non-square
    mmc.setProperty("Camera", "OnCameraCCDYSize", 500)

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=10000):
        _exp.buttons_wdg.run_button.click()

    assert exp_seq is not None
    data_shape = main_window.viewer.layers[-1].data.shape
    expected_shape = list(exp_seq.shape) + [500, 512]

    if Tr:
        expected_shape.pop(list(exp_seq.used_axes).index("p"))

    assert data_shape == tuple(expected_shape)

    if Tr:
        assert [p.name for p in tmp_path.iterdir()] == ["explorer_scan_000"]
        folder = tmp_path / "explorer_scan_000"
        assert len([p.name for p in folder.iterdir()]) == 2
    else:
        assert [p.name for p in tmp_path.iterdir()] == [f"{NAME}_000.tif"]

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pymmcore_plus.mda import MDAEngine
from pymmcore_widgets._zstack_widget import ZRangeAroundSelect

from micromanager_gui._gui_objects._sample_explorer_widget import SampleExplorer
from micromanager_gui._mda_meta import SEQUENCE_META
from micromanager_gui._util import event_indices

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

    main_window._show_dock_widget("Explorer")
    explorer = main_window._dock_widgets["Explorer"].widget()
    assert isinstance(explorer, SampleExplorer)
    explorer.scan_size_spinBox_r.setValue(2)
    explorer.scan_size_spinBox_c.setValue(2)
    explorer.ovelap_spinBox.setValue(0)
    explorer.channel_groupbox.add_ch_button.click()
    explorer.radiobtn_grid.setChecked(True)

    assert not main_window.viewer.layers

    assert explorer._set_grid() == [
        ("Grid_001_Pos000", -256.0, 256.0, 0.0),
        ("Grid_001_Pos001", 256.0, 256.0, 0.0),
        ("Grid_001_Pos002", 256.0, -256.0, 0.0),
        ("Grid_001_Pos003", -256.0, -256.0, 0.0),
    ]

    uid = None
    meta = None

    @mmc.mda.events.sequenceStarted.connect
    def get_seq(seq: MDASequence):
        nonlocal uid, meta
        meta = SEQUENCE_META[seq]
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
    assert _layer.metadata["uid"] == uid
    assert _layer.metadata["grid"] == "001"
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
    _exp = main_window._dock_widgets["Explorer"].widget()
    assert isinstance(_exp, SampleExplorer)
    _exp.save_explorer_groupbox.setChecked(True)
    _exp.dir_explorer_lineEdit.setText(str(tmp_path))
    _exp.fname_explorer_lineEdit.setText(NAME)

    _exp.scan_size_spinBox_r.setValue(2)
    _exp.scan_size_spinBox_c.setValue(1)
    _exp.ovelap_spinBox.setValue(0)

    _exp.time_groupbox.setChecked(bool(T))
    _exp.time_groupbox.time_comboBox.setCurrentText("ms")
    _exp.time_groupbox.timepoints_spinBox.setValue(3)
    _exp.time_groupbox.interval_spinBox.setValue(250)

    _exp.stack_groupbox.setChecked(bool(Z))
    _exp.stack_groupbox._zmode_tabs.setCurrentIndex(1)
    z_range_wdg = _exp.stack_groupbox._zmode_tabs.widget(1)
    assert isinstance(z_range_wdg, ZRangeAroundSelect)
    z_range_wdg._zrange_spinbox.setValue(3)
    _exp.stack_groupbox._zstep_spinbox.setValue(1)

    # 2 Channels
    _exp.channel_groupbox.add_ch_button.click()
    _exp.channel_groupbox.channel_tableWidget.cellWidget(0, 0).setCurrentText("DAPI")
    _exp.channel_groupbox.channel_tableWidget.cellWidget(0, 1).setValue(5)
    if C:
        _exp.channel_groupbox.add_ch_button.click()
        _exp.channel_groupbox.channel_tableWidget.cellWidget(1, 0).setCurrentText("Cy5")
        _exp.channel_groupbox.channel_tableWidget.cellWidget(1, 1).setValue(5)

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

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=4000):
        _exp.buttons_wdg.run_button.click()

    assert exp_seq is not None
    data_shape = main_window.viewer.layers[-1].data.shape
    expected_shape = list(exp_seq.shape) + [500, 512]

    if Tr:
        expected_shape.pop(list(event_indices(next(exp_seq.iter_events()))).index("p"))

    assert data_shape == tuple(expected_shape)

    if Tr:
        assert [p.name for p in tmp_path.iterdir()] == ["explorer_scan_000"]
        folder = tmp_path / "explorer_scan_000"
        assert len([p.name for p in folder.iterdir()]) == 2
    else:
        assert [p.name for p in tmp_path.iterdir()] == [f"{NAME}_000.tif"]

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from pymmcore_plus.mda import MDAEngine
from useq import MDASequence

from micromanager_gui import _mda_meta
from micromanager_gui._util import event_indices
from micromanager_gui.main_window import MainWindow

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_main_window_mda(main_window: MainWindow):

    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
    )

    _mda_meta.SEQUENCE_META[mda] = _mda_meta.SequenceMeta(mode="mda")
    main_window._on_meta_info(_mda_meta.SEQUENCE_META[mda], mda)

    mmc = main_window._mmc

    mmc.mda.events.sequenceStarted.emit(mda)

    img_shape = (mmc.getImageWidth(), mmc.getImageHeight())
    for event in mda:
        frame = np.random.rand(*img_shape)
        mmc.mda.events.frameReady.emit(frame, event)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 512, 512)


@pytest.mark.parametrize("Z", ["", "withZ"])
@pytest.mark.parametrize("splitC", ["", "splitC"])
@pytest.mark.parametrize("C", ["", "withC"])
@pytest.mark.parametrize("T", ["", "withT"])
def test_saving_mda(
    qtbot: QtBot, main_window: MainWindow, T, C, splitC, Z, tmp_path: Path
):

    NAME = "test_mda"
    _mda = main_window.mda
    _mda.save_groupbox.setChecked(True)
    _mda.dir_lineEdit.setText(str(tmp_path))
    _mda.fname_lineEdit.setText(NAME)

    _mda.time_groupbox.setChecked(bool(T))
    _mda.time_comboBox.setCurrentText("ms")
    _mda.timepoints_spinBox.setValue(3)
    _mda.interval_spinBox.setValue(250)

    _mda.stack_groupbox.setChecked(bool(Z))
    _mda.zrange_spinBox.setValue(3)
    _mda.step_size_doubleSpinBox.setValue(1)

    # 2 Channels
    _mda.add_ch_button.click()
    _mda.channel_tableWidget.cellWidget(0, 0).setCurrentText("DAPI")
    _mda.channel_tableWidget.cellWidget(0, 1).setValue(5)
    if C:
        _mda.add_ch_button.click()
        _mda.channel_tableWidget.cellWidget(1, 1).setValue(5)
    if splitC:
        _mda.checkBox_split_channels.setChecked(True)

    mda: MDASequence = None

    mmc = main_window._mmc
    # re-register twice to fully exercise the logic of the update
    # functions - the initial connections are made in init
    # then after that they are fully handled by the _update_mda_engine
    # callbacks
    mmc.register_mda_engine(MDAEngine(mmc))
    mmc.register_mda_engine(MDAEngine(mmc))

    @mmc.mda.events.sequenceStarted.connect
    def _store_mda(_mda):
        nonlocal mda
        mda = _mda

    # make the images non-square
    mmc.setProperty("Camera", "OnCameraCCDYSize", 500)

    with qtbot.waitSignals(
        [main_window.mda.metadataInfo, mmc.mda.events.sequenceFinished], timeout=4000
    ):
        main_window.mda.run_Button.click()

    assert mda is not None
    data_shape = main_window.viewer.layers[-1].data.shape
    expected_shape = list(mda.shape) + [500, 512]
    if splitC:
        expected_shape.pop(list(event_indices(next(mda.iter_events()))).index("c"))
    # back to tuple after manipulations with pop
    # need to be tuple to compare equality to a tuple
    expected_shape = tuple(expected_shape)

    assert data_shape == expected_shape

    if splitC:
        nfiles = len(list((tmp_path / f"{NAME}_000").iterdir()))
        assert nfiles == 2 if C else 1
    else:
        assert [p.name for p in tmp_path.iterdir()] == [f"{NAME}_000.tif"]
        assert data_shape == expected_shape


def test_script_initiated_mda(main_window: MainWindow, qtbot: QtBot):
    # we should show the mda even if it came from outside
    mmc = main_window._mmc
    sequence = MDASequence(
        channels=[{"config": "Cy5", "exposure": 1}, {"config": "FITC", "exposure": 1}],
        time_plan={"interval": 0.1, "loops": 2},
        z_plan={"range": 4, "step": 5},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
    )

    _mda_meta.SEQUENCE_META[sequence] = _mda_meta.SequenceMeta(mode="mda")
    main_window._on_meta_info(_mda_meta.SEQUENCE_META[sequence], sequence)

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=2000):
        mmc.run_mda(sequence)

    layer_name = f"Exp_{sequence.uid}"
    viewer = main_window.viewer
    viewer_layer_names = [layer.name for layer in viewer.layers]
    assert layer_name in viewer_layer_names
    assert sequence.shape == viewer.layers[layer_name].data.shape[:-2]

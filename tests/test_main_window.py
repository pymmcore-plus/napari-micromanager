from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np
import pytest
from pymmcore_plus.mda import MDAEngine
from useq import MDASequence

from micromanager_gui import _mda
from micromanager_gui._util import event_indices
from micromanager_gui.main_window import MainWindow

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.mark.parametrize("zarr", ["zarr", "numpy"])
def test_main_window_mda(main_window: MainWindow, zarr):

    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
    )

    mmc = main_window._mmc
    _mda.SEQUENCE_META[mda] = _mda.SequenceMeta(mode="mda")

    if zarr == "numpy":
        with patch("micromanager_gui.main_window.zarr", None):
            mmc.mda.events.sequenceStarted.emit(mda)
    else:
        mmc.mda.events.sequenceStarted.emit(mda)

    img_shape = (mmc.getImageWidth(), mmc.getImageHeight())
    for event in mda:
        frame = np.random.rand(*img_shape)
        mmc.mda.events.frameReady.emit(frame, event)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 512, 512)


@pytest.mark.parametrize("zarr", ["zarr", "numpy"])
@pytest.mark.parametrize("Z", ["", "withZ"])
@pytest.mark.parametrize("splitC", ["", "splitC"])
@pytest.mark.parametrize("C", ["", "withC"])
@pytest.mark.parametrize("T", ["", "withT"])
def test_saving_mda(qtbot: "QtBot", main_window: MainWindow, T, C, splitC, Z, zarr):
    import tempfile

    do_save = True
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        NAME = "test_mda"
        _mda = main_window.mda
        _mda.save_groupBox.setChecked(do_save)
        _mda.dir_lineEdit.setText(str(tmp_path))
        _mda.fname_lineEdit.setText(NAME)

        _mda.time_groupBox.setChecked(bool(T))
        _mda.time_comboBox.setCurrentText("ms")
        _mda.timepoints_spinBox.setValue(3)
        _mda.interval_spinBox.setValue(1)

        _mda.stack_groupBox.setChecked(bool(Z))
        _mda.zrange_spinBox.setValue(3)
        _mda.step_size_doubleSpinBox.setValue(1)

        # 2 Channels
        _mda.add_ch_Button.click()
        _mda.channel_tableWidget.cellWidget(0, 0).setCurrentText("DAPI")
        _mda.channel_tableWidget.cellWidget(0, 1).setValue(5)
        if C:
            _mda.add_ch_Button.click()
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

        with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=2000):
            if zarr == "numpy":
                with patch("micromanager_gui.main_window.zarr", None):
                    _mda._on_run_clicked()
            else:
                _mda._on_run_clicked()

        assert mda is not None
        data_shape = main_window.viewer.layers[-1].data.shape
        expected = list(mda.shape) + [512, 512]
        if splitC:
            expected.pop(list(event_indices(next(mda.iter_events()))).index("c"))
        expected_shape = tuple(e for e in expected if e != 1)
        assert data_shape == expected_shape

        if do_save:
            if splitC:
                nfiles = len(list((tmp_path / f"{NAME}_000").iterdir()))
                assert nfiles == 2 if C else 1
            else:
                assert [p.name for p in tmp_path.iterdir()] == [f"{NAME}_000.tif"]
                assert data_shape == expected_shape


def test_script_initiated_mda(main_window: MainWindow, qtbot: "QtBot"):
    # we should show the mda even if it came from outside
    mmc = main_window._mmc
    sequence = MDASequence(
        channels=[{"config": "Cy5", "exposure": 1}, {"config": "FITC", "exposure": 1}],
        time_plan={"interval": 0.1, "loops": 2},
        z_plan={"range": 4, "step": 5},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
    )
    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=2000):
        mmc.run_mda(sequence)

    layer_name = f"Exp_{sequence.uid}"
    viewer = main_window.viewer
    viewer_layer_names = [layer.name for layer in viewer.layers]
    assert layer_name in viewer_layer_names
    assert sequence.shape == viewer.layers[layer_name].data.shape[:-2]

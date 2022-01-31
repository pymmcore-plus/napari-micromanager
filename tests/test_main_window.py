from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from pymmcore_plus import RemoteMMCore
from useq import MDASequence

from micromanager_gui.main_window import MainWindow
from micromanager_gui.multid_widget import SequenceMeta

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_exposure_changing(qtbot: "QtBot", main_window: MainWindow):
    mmc = main_window._mmc
    remote = isinstance(mmc, RemoteMMCore)

    # qtbot wait was breaking at times with pysygnal signals
    if remote:
        waitSignals = qtbot.waitSignals
        waitSignal = qtbot.waitSignal

    else:

        @contextmanager
        def waitSignals(*args):
            yield

        @contextmanager
        def waitSignal(*args):
            yield

    with waitSignals(
        [
            main_window.snap_channel_comboBox.currentTextChanged,
            mmc.events.exposureChanged,
        ]
    ):
        main_window.snap_channel_comboBox.setCurrentText("DAPI")

    assert main_window.exp_spinBox.value() == 1.0
    assert mmc.getExposure() == 1.0
    with waitSignal(mmc.events.exposureChanged):
        mmc.setExposure(15)

    # Cy3/Cy5 has exposure defined in config group and we should respect that.
    with waitSignals(
        [
            main_window.snap_channel_comboBox.currentTextChanged,
            mmc.events.exposureChanged,
        ]
    ):
        main_window.snap_channel_comboBox.setCurrentText("Cy5")
    assert main_window.exp_spinBox.value() == 200
    assert mmc.getExposure() == 200

    # back to DAPI - make sure our 15 stuck
    with waitSignals(
        [
            main_window.snap_channel_comboBox.currentTextChanged,
            mmc.events.exposureChanged,
        ]
    ):
        main_window.snap_channel_comboBox.setCurrentText("DAPI")
    assert main_window.exp_spinBox.value() == 15
    assert mmc.getExposure() == 15

    # Now rhodamine - should go to the default value of the cache
    with waitSignals(
        [
            main_window.snap_channel_comboBox.currentTextChanged,
            mmc.events.exposureChanged,
        ]
    ):
        main_window.snap_channel_comboBox.setCurrentText("Rhodamine")
    assert main_window.exp_spinBox.value() == 1
    assert mmc.getExposure() == 1


def test_main_window_mda(main_window: MainWindow):

    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
    )

    main_window.mda.SEQUENCE_META[mda] = SequenceMeta(mode="mda")

    for event in mda:
        frame = np.random.rand(128, 128)
        main_window._on_mda_frame(frame, event)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 128, 128)


@pytest.mark.parametrize("Z", ["", "withZ"])
@pytest.mark.parametrize("splitC", ["", "splitC"])
@pytest.mark.parametrize("C", ["", "withC"])
@pytest.mark.parametrize("T", ["", "withT"])
def test_saving_mda(qtbot: "QtBot", main_window: MainWindow, T, C, splitC, Z):
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

        mda = None

        @main_window._mmc.events.sequenceStarted.connect
        def _store_mda(_mda):
            nonlocal mda
            mda = _mda

        with qtbot.waitSignal(main_window._mmc.events.sequenceFinished, timeout=2000):
            _mda._on_run_clicked()

        assert mda is not None
        data_shape = main_window.viewer.layers[-1].data.shape
        if splitC:
            expected = list(mda.shape) + [512, 512]
            expected[main_window.viewer.dims.axis_labels.index("c")] = 1
            assert data_shape == tuple(expected)

        if do_save:
            if splitC:
                nfiles = len(list((tmp_path / f"{NAME}_000").iterdir()))
                assert nfiles == 2 if C else 1
            else:
                assert [p.name for p in tmp_path.iterdir()] == [f"{NAME}_000.tif"]
                assert data_shape == mda.shape + (512, 512)


def test_refresh_safety(main_window: MainWindow):
    mmc = main_window._mmc

    # change properties from their default values
    mmc.setConfig("Channel", "DAPI")
    mmc.setStateLabel("Objective", "Nikon 10X S Fluor")
    mmc.setProperty("Camera", "Binning", 4)
    mmc.setProperty("Camera", "BitDepth", "12")

    main_window._refresh_options()

    # check that nothing was changed

    assert "DAPI" == mmc.getCurrentConfig("Channel")
    assert "Nikon 10X S Fluor" == mmc.getStateLabel("Objective")
    assert "4" == mmc.getProperty("Camera", "Binning")
    assert "12" == mmc.getProperty("Camera", "BitDepth")


def test_crop_camera(main_window: MainWindow):

    assert not main_window.viewer.layers

    cbox = main_window.cam_roi_comboBox
    cam_roi_btn = main_window.crop_Button

    text, div = ("1/4", 2)

    cbox.setCurrentText(text)

    cam_roi_btn.click()

    assert len(main_window.viewer.layers) == 1

    crop_layer = main_window.viewer.layers[-1]
    assert crop_layer.data.shape == (512 // div, 512 // div)

    cbox.setCurrentText("Full")
    crop_layer = main_window.viewer.layers[-1]
    assert crop_layer.data.shape == (512, 512)


def test_objective_device_and_px_size(main_window: MainWindow):
    mmc = main_window._mmc

    # set 10x objective
    main_window.objective_comboBox.setCurrentText("10X")
    assert main_window.objective_comboBox.currentText() == "10X"
    assert mmc.getCurrentPixelSizeConfig() == "Res10x"

    # delete objective group configuration
    mmc.deleteConfigGroup("Objective")

    # refresh objective options
    main_window._refresh_objective_options()

    assert main_window.objective_comboBox.currentText() == "Nikon 10X S Fluor"

    # delete pixel size configuration
    mmc.deletePixelSizeConfig("Res10x")

    # refresh objective options
    main_window._refresh_objective_options()

    assert mmc.getCurrentPixelSizeConfig() == "px_size_Nikon 10X S Fluor"

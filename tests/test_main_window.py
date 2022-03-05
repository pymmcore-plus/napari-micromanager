from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from pymmcore_plus.mda import MDAEngine
from useq import MDASequence

from micromanager_gui import _mda
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

    mmc = main_window._mmc
    _mda.SEQUENCE_META[mda] = _mda.SequenceMeta(mode="mda")

    mmc.mda.events.sequenceStarted.emit(mda)

    for event in mda:
        frame = np.random.rand(128, 128)
        mmc.mda.events.frameReady.emit(frame, event)
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


def test_script_initiated_mda(main_window: MainWindow, qtbot: "QtBot"):
    # we should show the mda even if it came from outside
    mmc = main_window._mmc
    print(mmc.getLoadedDevices())
    sequence = MDASequence(
        channels=[{"config": "Cy5", "exposure": 3}, {"config": "FITC", "exposure": 5}],
        time_plan={"interval": 0.1, "loops": 2},
        z_plan={"range": 4, "step": 0.5},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
    )
    with qtbot.waitSignal(mmc.mda.events.sequenceFinished):
        mmc.run_mda(sequence)

    layer_name = f"Exp_{sequence.uid}"
    viewer = main_window.viewer
    viewer_layer_names = [layer.name for layer in viewer.layers]
    assert layer_name in viewer_layer_names
    assert sequence.shape == viewer.layers[layer_name].data.shape[:-2]


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

    assert main_window.stage_wdg.xy_device_comboBox.count() == 1
    assert main_window.stage_wdg.xy_device_comboBox.currentText() == "XY"

    assert main_window.stage_wdg.focus_device_comboBox.count() == 1
    assert main_window.stage_wdg.focus_device_comboBox.currentText() == "Z"

import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from napari import Viewer
from pymmcore_plus import server
from useq import MDASequence

import micromanager_gui
from micromanager_gui.main_window import MainWindow
from micromanager_gui.multid_widget import SequenceMeta

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


if not os.getenv("MICROMANAGER_PATH"):
    try:
        root = Path(micromanager_gui.__file__)
        mm_path = list(root.parent.glob("Micro-Manager*"))[0]
        os.environ["MICROMANAGER_PATH"] = str(mm_path)
    except IndexError:
        raise AssertionError(
            "MICROMANAGER_PATH env var was not set, and Micro-Manager "
            "installation was not found in this package.  Please run "
            "`python micromanager_gui/install_mm.py"
        )


# https://docs.pytest.org/en/stable/fixture.html
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
    )

    main_window.explorer.SEQUENCE_META[explorer] = SequenceMeta(mode="explorer")

    for event in explorer:
        frame = np.random.rand(512, 512)
        main_window.explorer._on_explorer_frame(frame, event)
    assert main_window.viewer.layers[-1].data.shape == (512, 512)
    assert len(main_window.viewer.layers) == 4

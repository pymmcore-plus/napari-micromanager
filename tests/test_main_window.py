import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from napari import Viewer
from pymmcore_plus import server
from pymmcore_plus.client._client import _get_remote_pid
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


def _cleanup_existing_server():
    proc = _get_remote_pid(server.DEFAULT_HOST, server.DEFAULT_PORT)
    if proc is not None:
        print("killing existing process")
        proc.kill()


# https://docs.pytest.org/en/stable/fixture.html
@pytest.fixture(params=["local", "remote"])
def main_window(qtbot, request):
    if request.param == "remote":
        _cleanup_existing_server()

    viewer = Viewer(show=False)
    win = MainWindow(viewer=viewer, remote=request.param == "remote")
    win._mmc.loadSystemConfiguration("demo")

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
    mmc.setStateLabel("Objective", "60X 1.2 Oil")
    mmc.setProperty("Camera", "Binning", 4)
    mmc.setProperty("Camera", "PixelType", "16bit")

    main_window._refresh_options()

    # check that nothing was changed

    assert "DAPI" == mmc.getCurrentConfig("Channel")
    assert "60X 1.2 Oil" == mmc.getStateLabel("Objective")
    assert 4 == mmc.getProperty("Camera", "Binning")
    assert "16bit" == mmc.getProperty("Camera", "PixelType")

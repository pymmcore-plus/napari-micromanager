from pathlib import Path
from typing import Tuple

import pytest
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QTableWidgetItem

from micromanager_gui import _core
from micromanager_gui._gui_objects._sample_explorer_widget._sample_explorer_widget import (  # noqa: E501
    MMExploreSample,
)
from micromanager_gui.main_window import MainWindow

ExplorerTuple = Tuple[MainWindow, MMExploreSample]


@pytest.fixture(params=["local"])
def global_mmcore(request):
    _core._SESSION_CORE = CMMCorePlus()  # refresh singleton
    if request.param == "remote":
        from pymmcore_plus import server

        server.try_kill_server()

    mmc = _core.get_core_singleton(remote=request.param == "remote")
    if len(mmc.getLoadedDevices()) < 2:
        mmc.loadSystemConfiguration(str(Path(__file__).parent / "test_config.cfg"))
    return mmc


@pytest.fixture
def main_window(global_mmcore, make_napari_viewer):
    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer)
    config_path = str(Path(__file__).parent / "test_config.cfg")
    win.cfg_wdg.cfg_LineEdit.setText(config_path)
    win._mmc.loadSystemConfiguration(config_path)
    return win


@pytest.fixture
def explorer_two_channels(main_window: MainWindow) -> ExplorerTuple:

    explorer = main_window.explorer
    explorer.scan_size_spinBox_r.setValue(2)
    explorer.scan_size_spinBox_c.setValue(2)
    explorer.ovelap_spinBox.setValue(0)
    explorer.add_ch_explorer_Button.click()
    explorer.channel_explorer_comboBox.setCurrentText("Cy5")
    explorer.add_ch_explorer_Button.click()
    explorer.channel_explorer_comboBox.setCurrentText("FITC")

    # set grids position
    explorer.stage_pos_groupBox.setChecked(True)
    pos_table = explorer.stage_tableWidget

    grids = [("Grid_001", 0.0, 0.0, 0.0), ("Grid_002", 0.0, 0.0, 0.0)]
    for idx, i in enumerate(grids):
        idx = pos_table.rowCount()
        pos_table.insertRow(idx)
        name = QTableWidgetItem(i[0])
        pos_table.setItem(idx, 0, name)
        x = QTableWidgetItem(str(i[1]))
        pos_table.setItem(idx, 1, x)
        y = QTableWidgetItem(str(i[2]))
        pos_table.setItem(idx, 2, y)
        z = QTableWidgetItem(str(i[3]))
        pos_table.setItem(idx, 3, z)

    # set z-stack
    explorer.stack_groupBox.setChecked(True)
    explorer.z_tabWidget.setCurrentIndex(1)
    explorer.zrange_spinBox.setValue(2)
    explorer.step_size_doubleSpinBox.setValue(1.0)

    # set timelapse
    # main_win.explorer.time_groupBox.setChecked(True)
    # main_win.explorer.timepoints_spinBox.setValue(2)
    # main_win.explorer.interval_spinBox.setValue(3)

    return main_window, explorer

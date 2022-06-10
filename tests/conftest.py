from pathlib import Path
from typing import Tuple

import pytest
from pymmcore_plus import CMMCorePlus

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
def explorer_one_channel(main_window: MainWindow) -> ExplorerTuple:

    explorer = main_window.explorer
    explorer.scan_size_spinBox_r.setValue(2)
    explorer.scan_size_spinBox_c.setValue(2)
    explorer.ovelap_spinBox.setValue(0)
    explorer.add_ch_explorer_Button.click()

    return main_window, explorer


@pytest.fixture
def explorer_two_channel(main_window: MainWindow) -> ExplorerTuple:

    explorer = main_window.explorer
    explorer.scan_size_spinBox_r.setValue(2)
    explorer.scan_size_spinBox_c.setValue(2)
    explorer.ovelap_spinBox.setValue(0)
    explorer.add_ch_explorer_Button.click()
    explorer.channel_explorer_comboBox.setCurrentText("Cy5")
    explorer.add_ch_explorer_Button.click()
    explorer.channel_explorer_comboBox.setCurrentText("FITC")

    return main_window, explorer

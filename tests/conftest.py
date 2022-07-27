from pathlib import Path

import pytest
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import _core as wdg_core

from micromanager_gui import _core as mm_core
from micromanager_gui.main_window import MainWindow


# to create a new CMMCorePlus() for every test
@pytest.fixture
def core(monkeypatch):
    new_core = CMMCorePlus()
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", new_core)
    return new_core


# to reset the _SESSION_CORE variable to None in micromanager_gui._core._SESSION_CORE
@pytest.fixture
def session_core_napari_micromanager(monkeypatch):
    monkeypatch.setattr("micromanager_gui._core._SESSION_CORE", None)


# to reset the _SESSION_CORE variable to None in pymmcore_widgets._core._SESSION_CORE
@pytest.fixture
def session_core_pymmcore_widgets(monkeypatch):
    monkeypatch.setattr("pymmcore_widgets._core._SESSION_CORE", None)


@pytest.fixture
def main_window(
    core: CMMCorePlus,
    session_core_napari_micromanager,
    session_core_pymmcore_widgets,
    make_napari_viewer,
):
    assert mm_core._SESSION_CORE is None
    assert wdg_core._SESSION_CORE is None

    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer)

    assert core == win._mmc
    assert mm_core._SESSION_CORE == core
    assert wdg_core._SESSION_CORE == core

    config_path = str(Path(__file__).parent / "test_config.cfg")
    win._mmc.loadSystemConfiguration(config_path)
    return win

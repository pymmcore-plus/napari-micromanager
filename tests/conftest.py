from pathlib import Path

import pytest
from pymmcore_plus import CMMCorePlus

from micromanager_gui.main_window import MainWindow


@pytest.fixture
def core(monkeypatch):
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", CMMCorePlus())


@pytest.fixture
def session_core(monkeypatch):
    monkeypatch.setattr("micromanager_gui._core._SESSION_CORE", None)


@pytest.fixture
def main_window(core: CMMCorePlus, session_core: CMMCorePlus, make_napari_viewer):
    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer)
    config_path = str(Path(__file__).parent / "test_config.cfg")
    win._mmc.loadSystemConfiguration(config_path)
    return win

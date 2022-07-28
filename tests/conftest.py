from pathlib import Path

import pytest
from pymmcore_plus import CMMCorePlus

from micromanager_gui.main_window import MainWindow


# to create a new CMMCorePlus() for every test
@pytest.fixture
def core(monkeypatch):
    new_core = CMMCorePlus()
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", new_core)
    return new_core


@pytest.fixture
def main_window(core: CMMCorePlus, make_napari_viewer):
    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer)
    assert core == win._mmc
    config_path = str(Path(__file__).parent / "test_config.cfg")
    win._mmc.loadSystemConfiguration(config_path)
    return win

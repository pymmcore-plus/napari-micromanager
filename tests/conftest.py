from pathlib import Path

import pytest

from micromanager_gui.main_window import MainWindow


@pytest.fixture
def main_window(make_napari_viewer):
    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer)
    config_path = str(Path(__file__).parent / "test_config.cfg")
    win.cfg_wdg.cfg_LineEdit.setText(config_path)
    win._mmc.loadSystemConfiguration(config_path)
    return win

import numpy as np
import pytest
from micromanager_gui.main_window import MainWindow
from useq import MDASequence


# https://docs.pytest.org/en/stable/fixture.html
@pytest.fixture
def main_window(qtbot, make_napari_viewer):
    # qtbot is, itself, a fixture provided by pytest-qt
    # that starts a QApp for us

    win = MainWindow(viewer=make_napari_viewer())
    win.load_cfg()
    return win


def test_main_window(main_window: MainWindow):
    assert main_window
    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
    )
    for event in mda:
        print(event.index)
        frame = np.random.rand(128, 128)
        main_window._on_mda_frame(frame, event)

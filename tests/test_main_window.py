import os
from pathlib import Path

import micromanager_gui
import numpy as np
import pytest
from micromanager_gui.main_window import MainWindow
from useq import MDASequence


# https://docs.pytest.org/en/stable/fixture.html
@pytest.fixture
def main_window(qtbot, make_napari_viewer):
    # qtbot is, itself, a fixture provided by pytest-qt
    # that starts a QApp for us

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

    win = MainWindow(viewer=make_napari_viewer())
    win._mmc.loadSystemConfiguration("demo")

    return win


def test_main_window(main_window: MainWindow):

    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
    )
    for event in mda:

        frame = np.random.rand(128, 128)
        main_window._on_mda_frame(frame, event)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 128, 128)

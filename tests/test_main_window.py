from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from napari_micromanager.main_window import MainWindow

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_main_window(qtbot: QtBot, core: CMMCorePlus) -> None:
    """Basic test to check that the main window can be created.

    This test should remain fast.
    """
    viewer = MagicMock()
    wdg = MainWindow(viewer)
    qtbot.addWidget(wdg)

    viewer.layers.events.connect.assert_called_once_with(wdg._update_max_min)
    wdg._snap()

    wdg._update_viewer()
    wdg._mmc.startContinuousSequenceAcquisition()
    wdg._mmc.stopSequenceAcquisition()
    wdg._update_viewer()

    wdg._cleanup()
    viewer.layers.events.disconnect.assert_called_once_with(wdg._update_max_min)

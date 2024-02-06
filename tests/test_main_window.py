from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import useq
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
    core.snap()

    wdg._core_link._update_viewer()
    wdg._mmc.startContinuousSequenceAcquisition()
    wdg._mmc.stopSequenceAcquisition()
    wdg._core_link._update_viewer()

    wdg._cleanup()
    viewer.layers.events.disconnect.assert_called_once_with(wdg._update_max_min)


def test_preview_while_mda(main_window: MainWindow, qtbot: QtBot):
    # we should show the mda even if it came from outside
    mmc = main_window._mmc
    viewer = main_window.viewer

    # make sure that preview is not updated during MDA
    seq = useq.MDASequence(channels=["FITC"])

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished):
        mmc.run_mda(seq)

    layers = [layer.name for layer in viewer.layers]
    assert "preview" not in layers

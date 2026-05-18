from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
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


@pytest.mark.parametrize(
    "is_running, mda_running",
    [(True, False), (False, True)],
    ids=["runner_started_latch_unset", "runner_exited_latch_set"],
)
def test_image_snapped_gate_closed_during_mda_signal_window(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    is_running: bool,
    mda_running: bool,
):
    """The preview gate must stay closed in both queued-signal race
    windows around an MDA: when the runner has started but the queued
    ``@ensure_main_thread`` ``_on_mda_started`` slot hasn't latched
    ``_mda_running`` yet, and when the runner has already exited
    (also after a mid-MDA cancel) but ``_on_mda_finished`` hasn't
    cleared the latch on the main thread. Either gate alone is
    insufficient; both must be checked.
    """
    core_link = main_window._core_link
    monkeypatch.setattr(main_window._mmc.mda, "is_running", lambda: is_running)
    monkeypatch.setattr(core_link._mda_handler, "_mda_running", mda_running)

    with patch.object(core_link, "_update_viewer") as mocked:
        core_link._image_snapped()
    mocked.assert_not_called()

"""Tests that MainWindow is released when the napari viewer is closed.

Regression test for the device-leak issue where a napari_micromanager
MainWindow is kept alive by Qt signal connections after the hosting
napari window is closed, which on real hardware keeps devices (e.g.
Andor Mosaic3) bound to the dead process and prevents a subsequent
process from loading the same MM cfg.
"""

from __future__ import annotations

import gc
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import napari

from napari_micromanager.main_window import MainWindow

if TYPE_CHECKING:
    import pytest
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


CONFIG = str(Path(__file__).parent / "test_config.cfg")


def test_main_window_released_after_viewer_close(
    qtbot: QtBot, qapp: Any, core: CMMCorePlus
) -> None:
    """After viewer.close(), MainWindow must not be kept alive by signals."""
    viewer = napari.Viewer(show=False)
    win = MainWindow(viewer=viewer)

    win_ref = weakref.ref(win)

    viewer.close()
    # pump the Qt event loop so deleteLater()/destroyed can fire — this is what
    # happens naturally when the user closes the napari window while the GUI
    # event loop is running.
    qapp.processEvents()
    del win
    del viewer
    for _ in range(3):
        gc.collect()
    qapp.processEvents()
    for _ in range(3):
        gc.collect()

    surviving = win_ref()
    if surviving is not None:
        # help diagnose: show what's holding it alive
        referrers = [
            f"{type(r).__name__}: {repr(r)[:160]}" for r in gc.get_referrers(surviving)
        ]
        raise AssertionError(
            "MainWindow was not released after viewer.close(). Its child "
            "widgets all hold `_mmc`, so on real hardware this pins the "
            "CMMCorePlus singleton and the device adapter's exclusive "
            "handle until the entire Python process exits.\n"
            f"Referrers ({len(referrers)}):\n  " + "\n  ".join(referrers)
        )


def test_cleanup_unloads_devices_when_owned(
    qtbot: QtBot, napari_viewer: napari.Viewer
) -> None:
    """Owned core: _cleanup releases all device adapters."""
    win = MainWindow(viewer=napari_viewer)
    qtbot.addWidget(win)
    win._mmc.loadSystemConfiguration(CONFIG)
    assert len(win._mmc.getLoadedDevices()) > 1

    win._cleanup()

    # only the built-in "Core" pseudo-device should remain
    assert len(win._mmc.getLoadedDevices()) <= 1


def test_cleanup_preserves_external_core(
    qtbot: QtBot, napari_viewer: napari.Viewer, core: CMMCorePlus
) -> None:
    """External core: _cleanup must not unload devices the caller still uses."""
    before = len(core.getLoadedDevices())
    assert before > 1

    win = MainWindow(viewer=napari_viewer, mmcore=core)
    qtbot.addWidget(win)
    win._cleanup()

    assert len(core.getLoadedDevices()) == before


def test_cleanup_cancels_mda_when_owned(
    qtbot: QtBot,
    napari_viewer: napari.Viewer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owned core: _cleanup cancels any MDA the plugin may have started."""
    win = MainWindow(viewer=napari_viewer)
    qtbot.addWidget(win)
    cancel = MagicMock()
    monkeypatch.setattr(win._mmc.mda, "cancel", cancel)

    win._cleanup()

    cancel.assert_called_once()


def test_cleanup_does_not_cancel_external_mda(
    qtbot: QtBot,
    napari_viewer: napari.Viewer,
    core: CMMCorePlus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """External core: _cleanup must not cancel an MDA the caller may be running."""
    win = MainWindow(viewer=napari_viewer, mmcore=core)
    qtbot.addWidget(win)
    cancel = MagicMock()
    monkeypatch.setattr(core.mda, "cancel", cancel)

    win._cleanup()

    cancel.assert_not_called()

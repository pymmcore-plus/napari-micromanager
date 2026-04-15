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
from typing import TYPE_CHECKING, Any

import napari

from napari_micromanager.main_window import MainWindow

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


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
            f"{type(r).__name__}: {repr(r)[:160]}"
            for r in gc.get_referrers(surviving)
        ]
        raise AssertionError(
            "MainWindow was not released after viewer.close(). Its child "
            "widgets all hold `_mmc`, so on real hardware this pins the "
            "CMMCorePlus singleton and the device adapter's exclusive "
            "handle until the entire Python process exits.\n"
            f"Referrers ({len(referrers)}):\n  " + "\n  ".join(referrers)
        )

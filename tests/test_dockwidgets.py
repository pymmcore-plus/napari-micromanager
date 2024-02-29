from __future__ import annotations

from typing import TYPE_CHECKING

from napari_micromanager._gui_objects._toolbar import DOCK_WIDGETS

if TYPE_CHECKING:
    from pathlib import Path

    from napari_micromanager.main_window import MainWindow


def test_dockwidgets(main_window: MainWindow, saved_layout: Path):
    assert not saved_layout.exists()

    for dw_name in DOCK_WIDGETS:
        assert dw_name not in main_window._dock_widgets
        main_window._show_dock_widget(dw_name)
        main_window._dock_widgets[dw_name].close()

    # a layout file should have been saved
    assert saved_layout.exists()
    saved_layout.unlink()

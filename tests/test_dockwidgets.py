from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QPushButton

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

    from micromanager_gui.main_window import MainWindow


def test_dockwidgets(main_window: MainWindow, qtbot: QtBot):

    btn = QPushButton()
    btn.clicked.connect(main_window._show_dock_widget)

    doc_wdgs = main_window.DOCK_WIDGETS
    for dw_name in doc_wdgs:
        assert doc_wdgs[dw_name]["dockwidget"] is None
        btn.setText(dw_name)
        btn.click()
        dockwidget = doc_wdgs[dw_name]["dockwidget"]
        assert dockwidget.name == dw_name
        dockwidget.close()

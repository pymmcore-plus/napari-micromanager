import sys
from qtpy.QtWidgets import QApplication
import napari

from main_window import MainWindow

with napari.gui_qt():
    viewer = napari.Viewer()
    win = MainWindow(viewer)
    viewer.window.add_dock_widget(win, area="right", allowed_areas=["left", "right"])

    ###Set the viewer size as the screen size
    app = QApplication.instance()
    V = app.desktop().screenGeometry()
    screen_height = V.height()
    screen_width = V.width()
    viewer.window._qt_window.setGeometry(0, 0, screen_width, screen_height)
    viewer.window.window_menu




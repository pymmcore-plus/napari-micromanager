# import napari

# # from micromanager_gui.main_window import MainWindow
# from main_window import MainWindow

# viewer = napari.Viewer()
# win = MainWindow(viewer)
# viewer.window.add_dock_widget(win, area="right", allowed_areas=["left", "right"])
# viewer.window._qt_window.showFullScreen()
# napari.run()

import sys
# from qtpy.QtWidgets import QApplication
import napari

from main_window import MainWindow

with napari.gui_qt():
    viewer = napari.Viewer()
    win = MainWindow(viewer)
    viewer.window.add_dock_widget(win, area="right", allowed_areas=["left", "right"])
    viewer.window._qt_window.showFullScreen()


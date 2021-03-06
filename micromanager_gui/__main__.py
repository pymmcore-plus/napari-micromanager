import napari
from micromanager_gui.main_window import MainWindow

viewer = napari.Viewer()
win = MainWindow(viewer)
viewer.window.add_dock_widget(win, area="right", allowed_areas=["left", "right"])
viewer.window._qt_window.showFullScreen()
napari.run()

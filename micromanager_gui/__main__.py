import napari

from micromanager_gui.main_window import MainWindow

viewer = napari.Viewer()
win = MainWindow(viewer)
viewer.window.add_dock_widget(
    win, name="MicroManager", area="right", allowed_areas=["left", "right"]
)
napari.run()

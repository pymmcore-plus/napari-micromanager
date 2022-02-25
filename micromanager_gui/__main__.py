import napari

from micromanager_gui.main_window import MainWindow

viewer = napari.Viewer()
win = MainWindow(viewer, remote=False, log=True)
viewer.window.add_dock_widget(
    win, name="Micro-Manager", area="right", allowed_areas=["left", "right"]
)
napari.run()

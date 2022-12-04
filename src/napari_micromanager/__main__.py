import napari
from napari_micromanager.main_window import MainWindow

viewer = napari.Viewer()
win = MainWindow(viewer)
viewer.window.add_dock_widget(win, name="MicroManager", area="top")._close_btn = False
napari.run()

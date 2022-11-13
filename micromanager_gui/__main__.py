import napari

from micromanager_gui.main_window import MainWindow

viewer = napari.Viewer()

main_window = MainWindow(viewer)
main_window_dock = viewer.window.add_dock_widget(
    main_window,
    name="MicroManager",
    area="top",
    allowed_areas=["left", "right"],
    add_vertical_stretch=False,
)

napari.run()

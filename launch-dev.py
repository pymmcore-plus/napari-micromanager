import napari

v = napari.Viewer()
dw, main_window = v.window.add_plugin_dock_widget("micromanager")

core = main_window._mmc
core.loadSystemConfiguration("micromanager_gui/demo_config.cfg")

napari.run()

from pathlib import Path

import napari

v = napari.Viewer()
dw, main_window = v.window.add_plugin_dock_widget("micromanager")

core = main_window._mmc
core.loadSystemConfiguration(str(Path(__file__).parent / "tests" / "test_config.cfg"))

napari.run()

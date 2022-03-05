from pathlib import Path

import napari
from useq import MDASequence

v = napari.Viewer()
dw, main_window = v.window.add_plugin_dock_widget("napari-micromanager")

core = main_window._mmc
core.loadSystemConfiguration(str(Path(__file__).parent / "tests" / "test_config.cfg"))

sequence = MDASequence(
    channels=["Cy5", {"config": "FITC", "exposure": 50}],
    time_plan={"interval": 2, "loops": 5},
    z_plan={"range": 4, "step": 0.5},
    axis_order="tpcz",
    stage_positions=[(222, 1, 1), (111, 0, 0)],
)

main_window.mda.set_state(sequence)
v.window._qt_viewer.console.push(
    {"main_window": main_window, "mmc": core, "sequence": sequence}
)

napari.run()

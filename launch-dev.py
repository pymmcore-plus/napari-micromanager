from pathlib import Path

import napari
import numpy as np
from useq import MDASequence

try:
    from mda_simulator.mmcore import FakeDemoCamera
except ModuleNotFoundError:
    FakeDemoCamera = None

v = napari.Viewer()
dw, main_window = v.window.add_plugin_dock_widget("napari-micromanager")

core = main_window._mmc
core.loadSystemConfiguration(str(Path(__file__).parent / "tests" / "test_config.cfg"))

if FakeDemoCamera is not None:
    # override snap to look at more realistic images from a microscoppe
    # with underlying random walk simulation of spheres
    # These act as though "Cy5" is BF and other channels are fluorescent
    fake_cam = FakeDemoCamera(timing=2)
    # make sure we start in a valid channel group
    core.setConfig("Channel", "Cy5")

sequence = MDASequence(
    channels=["Cy5", {"config": "FITC", "exposure": 10}],
    time_plan={"interval": 10, "loops": 5},
    z_plan={"range": 50, "step": 10},
    axis_order="tpcz",
    stage_positions=[(222, 1, 1), (111, 0, 0)],
)

main_window.mda.set_state(sequence)

# fill napari-console with useful variables
v.window._qt_viewer.console.push(
    {"main_window": main_window, "mmc": core, "sequence": sequence, "np": np}
)

napari.run()

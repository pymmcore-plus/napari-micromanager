from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus.mda import MDAEngine
from useq import MDASequence

from napari_micromanager._gui_objects._mda_widget import MultiDWidget
from napari_micromanager._util import NMM_METADATA_KEY

if TYPE_CHECKING:
    from pathlib import Path

    from pytestqt.qtbot import QtBot

    from napari_micromanager.main_window import MainWindow


def test_main_window_mda(main_window: MainWindow):
    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
    )

    main_window._mmc.mda.run(mda)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 512, 512)
    assert main_window.viewer.layers[-1].data.nchunks_initialized == 32

    # assert that the layer has the correct metadata
    layer_meta = main_window.viewer.layers[0].metadata.get(NMM_METADATA_KEY)
    keys = ["useq_sequence", "uid"]
    assert all(key in layer_meta for key in keys)


def test_saving_mda(
    qtbot: QtBot,
    main_window: MainWindow,
    mda_sequence_splits: MDASequence,
    tmp_path: Path,
) -> None:
    mda = mda_sequence_splits
    main_window._show_dock_widget("MDA")
    mda_widget = main_window._dock_widgets["MDA"].widget()
    assert isinstance(mda_widget, MultiDWidget)

    dest = tmp_path / "thing.ome.tif"

    mda_widget.setValue(mda)
    mda_widget.save_info.setValue(dest)
    assert mda_widget.save_info.isChecked()

    mmc = main_window._mmc

    # re-register twice to fully exercise the logic of the update
    # functions - the initial connections are made in init
    # then after that they are fully handled by the _update_mda_engine
    # callbacks
    mmc.register_mda_engine(MDAEngine(mmc))
    mmc.register_mda_engine(MDAEngine(mmc))

    # make the images non-square
    mmc.setProperty("Camera", "OnCameraCCDYSize", 500)
    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=8000):
        mda_widget.run_mda()

    expected_shape = [x for x in (*mda.shape, 500, 512) if x > 1]
    data_shape = [x for x in main_window.viewer.layers[-1].data.shape if x > 1]

    multiC = len(mda.channels) > 1
    splitC = mda.metadata[NMM_METADATA_KEY].get("split_channels")
    if multiC and splitC:
        expected_shape.pop(mda.used_axes.find("c"))

    assert dest.exists()
    assert data_shape == expected_shape


def test_script_initiated_mda(main_window: MainWindow, qtbot: QtBot) -> None:
    # we should show the mda even if it came from outside
    mmc = main_window._mmc
    sequence = MDASequence(
        channels=[{"config": "Cy5", "exposure": 1}, {"config": "FITC", "exposure": 1}],
        time_plan={"interval": 0.1, "loops": 2},
        z_plan={"range": 4, "step": 5},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
    )

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=5000):
        mmc.run_mda(sequence)

    layer_name = f"Exp_{sequence.uid}"
    viewer = main_window.viewer
    viewer_layer_names = [layer.name for layer in viewer.layers]
    assert layer_name in viewer_layer_names
    assert sequence.shape == viewer.layers[layer_name].data.shape[:-2]

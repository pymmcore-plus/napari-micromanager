from __future__ import annotations

from typing import TYPE_CHECKING

from napari_micromanager._gui_objects._mda_widget import MultiDWidget
from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from pymmcore_plus.mda import MDAEngine
from useq import MDASequence

if TYPE_CHECKING:
    from pathlib import Path

    from napari_micromanager.main_window import MainWindow
    from pytestqt.qtbot import QtBot


def test_main_window_mda(main_window: MainWindow):
    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
        metadata={SEQUENCE_META_KEY: SequenceMeta(mode="mda")},
    )

    main_window._mmc.mda.run(mda)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 512, 512)
    assert main_window.viewer.layers[-1].data.nchunks_initialized == 32


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

    # FIXME:
    # we have a bit of a battle here now for file-saving metadata between
    # pymmcore_widgets and napari_micromanager's SequenceMetadata
    # should standardize, possibly by adding to useq-schema
    # this test uses the pymmcore-widgets metadata for now
    widget_meta = mda.metadata.setdefault("pymmcore_widgets", {})
    widget_meta["save_dir"] = str(tmp_path)
    widget_meta["should_save"] = True

    mda_widget.setValue(mda)
    assert mda_widget.save_info.isChecked()
    meta = mda_widget.value().metadata[SEQUENCE_META_KEY]
    assert meta.save_dir == str(tmp_path)
    mda = mda.replace(axis_order=mda_widget.value().axis_order)

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
        mda_widget.control_btns.run_btn.click()

    data_shape = [x for x in main_window.viewer.layers[-1].data.shape if x > 1]
    expected_shape = [x for x in (*mda.shape, 500, 512) if x > 1]

    multiC = len(mda.channels) > 1
    splitC = mda.metadata[SEQUENCE_META_KEY].split_channels
    if multiC and splitC:
        expected_shape.pop(mda.used_axes.find("c"))
        nfiles = len(list((tmp_path / f"{meta.file_name}_000").iterdir()))
        assert nfiles == 2 if multiC else 1
    # splitC with one channel is the same as not split
    else:
        assert [p.name for p in tmp_path.iterdir()] == [f"{meta.file_name}_000.tif"]
    assert data_shape == expected_shape


def test_script_initiated_mda(main_window: MainWindow, qtbot: QtBot):
    # we should show the mda even if it came from outside
    mmc = main_window._mmc
    sequence = MDASequence(
        channels=[{"config": "Cy5", "exposure": 1}, {"config": "FITC", "exposure": 1}],
        time_plan={"interval": 0.1, "loops": 2},
        z_plan={"range": 4, "step": 5},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
        metadata={SEQUENCE_META_KEY: SequenceMeta(mode="mda")},
    )

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=5000):
        mmc.run_mda(sequence)

    layer_name = f"Exp_{sequence.uid}"
    viewer = main_window.viewer
    viewer_layer_names = [layer.name for layer in viewer.layers]
    assert layer_name in viewer_layer_names
    assert sequence.shape == viewer.layers[layer_name].data.shape[:-2]

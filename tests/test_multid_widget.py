from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from napari_micromanager._gui_objects._mda_widget import MultiDWidget
from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from napari_micromanager._util import event_indices
from napari_micromanager.main_window import MainWindow
from pymmcore_plus.mda import MDAEngine
from pymmcore_widgets._zstack_widget import ZRangeAroundSelect
from useq import MDASequence

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_main_window_mda(main_window: MainWindow):

    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
        metadata={SEQUENCE_META_KEY: SequenceMeta(mode="mda")},
    )

    mmc = main_window._mmc

    mmc.mda.events.sequenceStarted.emit(mda)

    img_shape = (mmc.getImageWidth(), mmc.getImageHeight())
    for event in mda:
        frame = np.random.rand(*img_shape)
        mmc.mda.events.frameReady.emit(frame, event)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 512, 512)


def test_saving_mda(
    qtbot: QtBot,
    main_window: MainWindow,
    mda_sequence_splits: MDASequence,
    tmp_path: Path,
) -> None:
    mda = mda_sequence_splits
    meta: SequenceMeta = mda.metadata[SEQUENCE_META_KEY]
    meta.save_dir = str(tmp_path)

    main_window._show_dock_widget("MDA")
    mda_widget = main_window._dock_widgets["MDA"].widget()
    assert isinstance(mda_widget, MultiDWidget)

    mmc = main_window._mmc
    # re-register twice to fully exercise the logic of the update
    # functions - the initial connections are made in init
    # then after that they are fully handled by the _update_mda_engine
    # callbacks
    mmc.register_mda_engine(MDAEngine(mmc))
    mmc.register_mda_engine(MDAEngine(mmc))

    # make the images non-square
    mmc.setProperty("Camera", "OnCameraCCDYSize", 500)
    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=10000):
        # mda_widget.buttons_wdg.run_button.click()
        mmc.run_mda(mda)

    data_shape = main_window.viewer.layers[-1].data.shape
    expected_shape = list(mda.shape) + [500, 512]

    multiC = len(mda.channels) > 1

    if multiC and meta.split_channels:
        expected_shape.pop(list(event_indices(next(mda.iter_events()))).index("c"))

    assert data_shape == tuple(expected_shape)

    if multiC and meta.split_channels:
        nfiles = len(list((tmp_path / f"{meta.file_name}_000").iterdir()))
        assert nfiles == 2 if multiC else 1
    else:
        assert [p.name for p in tmp_path.iterdir()] == [f"{meta.file_name}_000.tif"]
        assert data_shape == tuple(expected_shape)


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

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=2000):
        mmc.run_mda(sequence)

    layer_name = f"Exp_{sequence.uid}"
    viewer = main_window.viewer
    viewer_layer_names = [layer.name for layer in viewer.layers]
    assert layer_name in viewer_layer_names
    assert sequence.shape == viewer.layers[layer_name].data.shape[:-2]

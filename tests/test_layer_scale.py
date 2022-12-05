from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from napari_micromanager.main_window import MainWindow
from useq import MDASequence

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.mark.parametrize("Z", ["", "withZ"])
@pytest.mark.parametrize("C", ["", "withC"])
@pytest.mark.parametrize("splitC", ["", "splitC"])
@pytest.mark.parametrize("T", ["", "withT"])
def test_layer_scale(qtbot: QtBot, main_window: MainWindow, Z, C, splitC, T):

    Z_RANGE = 5
    STEP_SIZE = 2

    mmc = main_window._mmc
    mmc.setProperty("Objective", "Label", "Nikon 20X Plan Fluor ELWD")

    for order in ["tpcz", "tpzc", "ptcz", "ptzc"]:
        sequence = MDASequence(
            axis_order=order,
            channels=["DAPI", "Cy5"] if (C and splitC) else ["DAPI"],
            z_plan={"range": Z_RANGE, "step": STEP_SIZE} if Z else {},
            time_plan={"interval": 1, "loops": 2} if T else {},
        )
        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda", split_channels=bool(C and splitC)
        )

        # create zarr layer
        main_window._on_mda_started(sequence)
        assert len(list(main_window.viewer.layers)) == 2 if (C and splitC) else 1

        layer = main_window.viewer.layers[0]
        if Z:
            assert layer.scale[layer.data.shape.index(len(sequence.z_plan))] == float(
                STEP_SIZE
            )
        else:
            for idx, val in enumerate(reversed(layer.scale)):
                if idx <= 1:
                    assert val == mmc.getPixelSizeUm()
                else:
                    assert val == 1.0
        main_window.viewer.layers.clear()
        assert not list(main_window.viewer.layers)

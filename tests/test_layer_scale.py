from __future__ import annotations

import pytest
from napari_micromanager._mda_handler import _NapariMDAHandler
from pymmcore_plus import CMMCorePlus
from useq import MDASequence


@pytest.mark.parametrize("axis_order", ["tpcz", "tpzc"])
def test_layer_scale(
    make_napari_viewer,
    mda_sequence_splits: MDASequence,
    axis_order: str,
) -> None:
    mmc = CMMCorePlus.instance()
    mmc.loadSystemConfiguration()
    viewer = make_napari_viewer()
    handler = _NapariMDAHandler(mmc, viewer)

    mmc.setProperty("Objective", "Label", "Nikon 20X Plan Fluor ELWD")
    sequence = mda_sequence_splits.replace(axis_order=axis_order)
    z_step = sequence.z_plan and sequence.z_plan.step

    # create zarr layer
    handler._on_mda_started(sequence)

    layer = viewer.layers[0]
    if sequence.z_plan:
        assert layer.scale[layer.data.shape.index(len(sequence.z_plan))] == z_step
    else:
        expect = [1] * (layer.data.ndim - 2) + [mmc.getPixelSizeUm()] * 2
        assert tuple(layer.scale) == tuple(expect)

    handler._cleanup()

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from napari_micromanager._mda_handler import _NapariMDAHandler
from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from pymmcore_plus import CMMCorePlus

if TYPE_CHECKING:
    from napari_micromanager.main_window import MainWindow
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

    sequence = mda_sequence_splits.replace(
        axis_order=axis_order,
        metadata={SEQUENCE_META_KEY: SequenceMeta(should_save=False)},
    )
    z_step = sequence.z_plan and sequence.z_plan.step

    # create zarr layer
    handler._on_mda_started(sequence)

    layer = viewer.layers[0]
    if sequence.z_plan:
        num_z = len(list(sequence.z_plan))
        assert layer.scale[layer.data.shape.index(num_z)] == z_step
    else:
        expect = [1] * (layer.data.ndim - 2) + [mmc.getPixelSizeUm()] * 2
        assert tuple(layer.scale) == tuple(expect)

    # cleanup zarr resources
    handler._cleanup()
    handler._on_mda_finished(sequence)

    # now pretend that the user never provided a pixel size config
    # we need to not crash in this case

    pix_size = mmc.getPixelSizeUm()
    mmc.setPixelSizeUm("Res20x", 0)

    try:
        handler._on_mda_started(sequence)
    except Exception as e:
        # return to orig value for future tests and re-raise
        mmc.setPixelSizeUm(pix_size)
        # cleanup zarr resources
        handler._cleanup()
        raise e
    # cleanup zarr resources
    handler._cleanup()
    handler._on_mda_finished(sequence)


def test_preview_scale(core: CMMCorePlus, main_window: MainWindow):
    """Basic test to check that the main window can be created.

    This test should remain fast.
    """
    img = core.snap()
    main_window._update_viewer(img)

    pix_size = core.getPixelSizeUm()
    assert tuple(main_window.viewer.layers["preview"].scale) == (pix_size, pix_size)

    # now pretend that the user never provided a pixel size config
    # we need to not crash in this case

    core.setPixelSizeUm("Res20x", 0)

    try:
        main_window._update_viewer(img)
    except Exception as e:
        # return to orig value for future tests and re-raise
        core.setPixelSizeUm(pix_size)
        raise e

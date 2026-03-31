from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import useq
from pymmcore_plus import CMMCorePlus

from napari_micromanager._mda_handler import _NapariMDAHandler
from napari_micromanager._util import NMM_METADATA_KEY

if TYPE_CHECKING:
    import napari

    from napari_micromanager.main_window import MainWindow

CONFIG = str(Path(__file__).parent / "test_config.cfg")

_SCALE_SEQUENCES = [
    pytest.param(
        useq.MDASequence(
            channels=[useq.Channel(config="DAPI", exposure=5)],
            metadata={NMM_METADATA_KEY: {"split_channels": False}},
        ),
        id="no_z",
    ),
    pytest.param(
        useq.MDASequence(
            z_plan=useq.ZRangeAround(range=3, step=0.5),
            channels=[useq.Channel(config="DAPI", exposure=5)],
            metadata={NMM_METADATA_KEY: {"split_channels": False}},
        ),
        id="with_z",
    ),
]


@pytest.mark.parametrize("axis_order", ["tpcz", "tpzc"])
@pytest.mark.parametrize("sequence", _SCALE_SEQUENCES)
def test_layer_scale(
    napari_viewer: napari.Viewer,
    sequence: useq.MDASequence,
    axis_order: str,
) -> None:
    """Scale depends on z_plan step and pixel size, not on time/channel/split."""
    mmc = CMMCorePlus()
    mmc.loadSystemConfiguration(CONFIG)
    handler = _NapariMDAHandler(mmc, napari_viewer)

    mmc.setProperty("Objective", "Label", "Nikon 20X Plan Fluor ELWD")

    seq = sequence.replace(axis_order=axis_order)
    z_step = seq.z_plan and seq.z_plan.step

    handler._on_mda_started(seq)

    layer = napari_viewer.layers[0]
    if seq.z_plan:
        num_z = len(list(seq.z_plan))
        assert layer.scale[layer.data.shape.index(num_z)] == z_step
    else:
        expect = [1] * (layer.data.ndim - 2) + [mmc.getPixelSizeUm()] * 2
        assert tuple(layer.scale) == tuple(expect)

    handler._cleanup()
    handler._on_mda_finished(seq)

    # Now pretend that the user never provided a pixel size config.
    # We need to not crash in this case.
    pix_size = mmc.getPixelSizeUm()
    mmc.setPixelSizeUm("Res20x", 0)

    try:
        handler._on_mda_started(seq)
    except Exception as e:
        mmc.setPixelSizeUm(pix_size)
        handler._cleanup()
        raise e
    handler._cleanup()
    handler._on_mda_finished(seq)


def test_preview_scale(core: CMMCorePlus, main_window: MainWindow) -> None:
    img = core.snap()
    main_window._core_link._update_viewer(img)

    pix_size = core.getPixelSizeUm()
    assert tuple(main_window.viewer.layers["preview"].scale) == (pix_size, pix_size)

    core.setPixelSizeUm("Res20x", 0)

    try:
        main_window._core_link._update_viewer(img)
    except Exception as e:
        core.setPixelSizeUm(pix_size)
        raise e

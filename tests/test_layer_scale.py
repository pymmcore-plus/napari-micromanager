from __future__ import annotations

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from napari_micromanager.main_window import MainWindow
from useq import MDASequence


def test_layer_scale(main_window: MainWindow, mda_sequence_splits: MDASequence) -> None:

    mmc = main_window._mmc
    mmc.setProperty("Objective", "Label", "Nikon 20X Plan Fluor ELWD")

    for order in ["tpcz", "tpzc"]:
        sequence = mda_sequence_splits
        sequence = sequence.replace(axis_order=order)
        meta: SequenceMeta = sequence.metadata[SEQUENCE_META_KEY]
        sequence.metadata[SEQUENCE_META_KEY] = meta

        # create zarr layer
        main_window._on_mda_started(sequence)

        layer = main_window.viewer.layers[0]
        if sequence.z_plan:
            assert layer.scale[layer.data.shape.index(len(sequence.z_plan))] == 1.0
        else:
            for idx, val in enumerate(reversed(layer.scale)):
                if idx <= 1:
                    assert val == mmc.getPixelSizeUm()
                else:
                    assert val == 1.0
        main_window.viewer.layers.clear()
        assert not list(main_window.viewer.layers)

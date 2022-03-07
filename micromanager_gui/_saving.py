from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import tifffile

from ._util import ensure_unique

if TYPE_CHECKING:
    from napari.components import LayerList
    from useq import MDASequence

    from ._gui_objects._mda_widget import SequenceMeta


def _imsave(file: Path, data: np.ndarray, dtype="uint16"):
    tifffile.imwrite(str(file), data.astype(dtype), imagej=data.ndim <= 5)


def save_sequence(sequence: MDASequence, layers: LayerList, meta: SequenceMeta):
    if not meta.should_save:
        return
    if meta.mode == "mda":
        return _save_mda_sequence(sequence, layers, meta)
    if meta.mode == "explorer":
        return _save_explorer_scan(sequence, layers, meta)
    raise NotImplementedError(f"cannot save experiment with mode: {meta.mode}")


def _save_mda_sequence(sequence: MDASequence, layers: LayerList, meta: SequenceMeta):
    path = Path(meta.save_dir)
    file_name = meta.file_name
    folder_name = ensure_unique(path / file_name, extension="", ndigits=3)

    # if split_channels, then create a new layer for each channel
    if meta.split_channels:
        folder_name.mkdir(parents=True, exist_ok=True)

        if meta.save_pos:
            # save each position/channels in a separate file.
            _save_pos_separately(sequence, folder_name, folder_name.stem, layers)
        else:
            # save each channel layer.
            for lay in layers:
                if lay.metadata.get("uid") != sequence.uid:
                    continue
                fname = f'{folder_name.stem}_{lay.metadata.get("ch_id")}.tif'
                _imsave(folder_name / fname, lay.data.squeeze())
        return

    # not splitting channels
    active_layer = next(x for x in layers if x.metadata.get("uid") == sequence.uid)

    if meta.save_pos:
        folder_name.mkdir(parents=True, exist_ok=True)
        # save each position in a separate file
        pos_axis = sequence.axis_order.index("p")
        for p, data in enumerate(np.rollaxis(active_layer.data, pos_axis)):
            dest = folder_name / f"{folder_name.stem}_[p{p:03d}].tif"
            _imsave(dest, data)

    else:
        # not saving each position in a separate file
        save_path = ensure_unique(path / file_name, extension=".tif", ndigits=3)
        _imsave(save_path, active_layer.data.squeeze())


def _save_pos_separately(sequence, folder_name, fname, layers: LayerList):
    for p in range(len(sequence.stage_positions)):

        folder_path = Path(folder_name) / f"{fname}_Pos{p:03d}"
        folder_path.mkdir(parents=True, exist_ok=True)

        for i in layers:
            if "ch_id" not in i.metadata or i.metadata.get("uid") != sequence.uid:
                continue
            fname = f"{fname}_{i.metadata['ch_id']}_[p{p:03}]"
            ax = sequence.axis_order.index("p") if len(sequence.time_plan) > 0 else 0
            _imsave(folder_path / f"{fname}.tif", i.data.take(p, axis=ax))


def _save_explorer_scan(sequence: MDASequence, layers: LayerList, meta: SequenceMeta):

    path = Path(meta.save_dir)
    file_name = f"scan_{meta.file_name}"

    folder_name = ensure_unique(path / file_name, extension="", ndigits=3)
    folder_name.mkdir(parents=True, exist_ok=True)

    for layer in sorted(
        (i for i in layers if i.metadata.get("uid") == sequence.uid),
        key=lambda x: x.metadata.get("ch_id"),
    ):
        data = layer.data[np.newaxis, ...]

        if layer.metadata.get("scan_position") == "Pos000":
            scan_stack = data
        else:
            scan_stack = np.concatenate((scan_stack, data))

        if scan_stack.shape[0] > 1:
            ch_name = layer.metadata.get("ch_name")
            _imsave(folder_name / f"{ch_name}.tif", scan_stack)

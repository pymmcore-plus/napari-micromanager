from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import tifffile

from ._util import ensure_unique

if TYPE_CHECKING:
    from napari.components import LayerList
    from useq import MDASequence

    from napari_micromanager._mda_meta import SequenceMeta


def _imsave(file: Path, data: np.ndarray, dtype: str = "uint16") -> None:
    tifffile.imwrite(
        str(file), data.astype(dtype), imagej=data.ndim <= 5, photometric="MINISBLACK"
    )


def save_sequence(sequence: MDASequence, layers: LayerList, meta: SequenceMeta) -> None:
    """Save `layers` associated with an MDA `sequence` to disk.

    Parameters
    ----------
    sequence : MDASequence
        An MDA sequence being run.
    layers : LayerList
        A list of layers acquired during the MDA sequence.
    meta : SequenceMeta
        Internal metadata associated with the sequence.
    """
    if not meta:
        return
    if not meta.should_save:
        return
    if meta.mode in ("mda", ""):
        return _save_mda_sequence(sequence, layers, meta)
    raise NotImplementedError(f"cannot save experiment with mode: {meta.mode}")


def _save_mda_sequence(
    sequence: MDASequence, layers: LayerList, meta: SequenceMeta
) -> None:
    path = Path(meta.save_dir)
    file_name = meta.file_name
    folder_name = ensure_unique(path / file_name, extension="", ndigits=3)

    mda_layers = [i for i in layers if i.metadata.get("uid") == sequence.uid]
    # if split_channels, then create a new layer for each channel
    if meta.split_channels:
        folder_name.mkdir(parents=True, exist_ok=True)

        if meta.save_pos:
            # save each position/channels in a separate file.
            _save_pos_separately(sequence, folder_name, folder_name.stem, mda_layers)
        else:
            # save each channel layer.
            for lay in mda_layers:
                fname = f'{folder_name.stem}_{lay.metadata.get("ch_id")}.tif'
                # TODO: smarter behavior w.r.t type of lay.data
                # currently this will force the data into memory which may cause a crash
                # long term solution is to remove this code and rely on an
                # mda-writer either in pymmcore-plus or elsewhere.
                _imsave(folder_name / fname, np.squeeze(lay.data))
        return

    # not splitting channels
    active_layer = mda_layers[0]

    if meta.save_pos:
        # save each position in a separate file
        folder_name.mkdir(parents=True, exist_ok=True)
        for p in range(len(sequence.stage_positions)):
            dest = folder_name / f"{folder_name.stem}_p{p:03d}.tif"
            ax = 1 if sequence.sizes.get("t", 0) > 0 else 0
            pos_data = np.take(active_layer.data, 0, axis=ax)
            _imsave(dest, np.squeeze(pos_data))

    else:
        # not saving each position in a separate file
        save_path = ensure_unique(path / file_name, extension=".tif", ndigits=3)
        # TODO: see above TODO
        _imsave(save_path, np.squeeze(active_layer.data))


def _save_pos_separately(
    sequence: MDASequence, folder_name: Path, fname: str, layers: LayerList
) -> None:
    for p in range(len(sequence.stage_positions)):
        folder_path = folder_name / f"{fname}_Pos{p:03d}"
        folder_path.mkdir(parents=True, exist_ok=True)

        for i in layers:
            if "ch_id" not in i.metadata or i.metadata.get("uid") != sequence.uid:
                continue
            filename = f"{fname}_{i.metadata['ch_id']}_p{p:03}"
            ax = sequence.axis_order.index("p") if sequence.sizes.get("t", 0) > 0 else 0
            _imsave(folder_path / f"{filename}.tif", np.take(i.data, p, axis=ax))

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from platformdirs import user_config_dir
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QFileDialog, QWidget

if TYPE_CHECKING:
    import useq

USER_DIR = Path(user_config_dir("napari_micromanager"))
USER_CONFIGS_PATHS = USER_DIR / "system_configurations.json"

# key in MDASequence.metadata to store napari-micromanager metadata
# note that this is also used in napari layer metadata
NMM_METADATA_KEY = "napari_micromanager"
try:
    from pymmcore_widgets.useq_widgets import PYMMCW_METADATA_KEY as PYMMCW_METADATA_KEY
except ImportError:
    # key in MDASequence.metadata where we expect to find pymmcore_widgets metadata
    PYMMCW_METADATA_KEY = "pymmcore_widgets"

try:
    from pymmcore_plus.mda.handlers._util import (
        get_full_sequence_axes as get_full_sequence_axes,
    )
except ImportError:

    def get_full_sequence_axes(sequence: useq.MDASequence) -> tuple[str, ...]:
        """Get the combined axes from sequence and sub-sequences."""
        # axes main sequence
        main_seq_axes = list(sequence.used_axes)
        if not sequence.stage_positions:
            return tuple(main_seq_axes)
        # axes from sub sequences
        sub_seq_axes: list = []
        for p in sequence.stage_positions:
            if p.sequence is not None:
                sub_seq_axes.extend(
                    [ax for ax in p.sequence.used_axes if ax not in main_seq_axes]
                )
        return tuple(main_seq_axes + sub_seq_axes)


def ensure_unique(path: Path, extension: str = ".tif", ndigits: int = 3) -> Path:
    """Get next suitable filepath (extension = ".tif") or folderpath (extension = "").

    Result is appended with a counter of ndigits.
    """
    p = path
    stem = p.stem
    # check if provided path already has an ndigit number in it
    cur_num = stem.rsplit("_")[-1]
    if cur_num.isdigit() and len(cur_num) == ndigits:
        stem = stem[: -ndigits - 1]
        current_max = int(cur_num) - 1
    else:
        current_max = -1

    # # find the highest existing path (if dir)
    paths = (
        p.parent.glob(f"*{extension}")
        if extension
        else (f for f in p.parent.iterdir() if f.is_dir())
    )
    for fn in paths:
        try:
            current_max = max(current_max, int(fn.stem.rsplit("_")[-1]))
        except ValueError:
            continue

    # build new path name
    number = f"_{current_max+1:0{ndigits}d}"
    return path.parent / f"{stem}{number}{extension}"


def add_path_to_config_json(path: Path | str) -> None:
    """Update the stystem configurations json file with the new path."""
    import json

    if isinstance(path, Path):
        path = str(path)

    # create USER_CONFIGS_PATHS if it doesn't exist
    if not USER_CONFIGS_PATHS.exists():
        USER_DIR.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIGS_PATHS, "w") as f:
            json.dump({"paths": []}, f)

    # Read the existing data
    try:
        with open(USER_CONFIGS_PATHS) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = {"paths": []}

    # Append the new path. using insert so we leave the empty string at the end
    paths = cast(list, data.get("paths", []))
    if path not in paths:
        paths.insert(0, path)

    # Write the data back to the file
    with open(USER_CONFIGS_PATHS, "w") as f:
        json.dump({"paths": paths}, f)


def save_sys_config_dialog(
    parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
) -> None:
    (filename, _) = QFileDialog.getSaveFileName(
        parent, "Save Micro-Manager Configuration."
    )
    if filename:
        filename = filename if str(filename).endswith(".cfg") else f"{filename}.cfg"
        mmcore = mmcore or CMMCorePlus.instance()
        mmcore.saveSystemConfiguration(filename)
        add_path_to_config_json(filename)


def load_sys_config_dialog(
    parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
) -> None:
    """Open file dialog to select a config file."""
    (filename, _) = QFileDialog.getOpenFileName(
        parent, "Select a Micro-Manager configuration file", "", "cfg(*.cfg)"
    )
    if filename:
        add_path_to_config_json(filename)
        mmcore = mmcore or CMMCorePlus.instance()
        mmcore.loadSystemConfiguration(filename)

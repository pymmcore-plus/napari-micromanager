import itertools
from pathlib import Path

import pytest
from napari_micromanager.main_window import MainWindow

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from pymmcore_plus import CMMCorePlus
from itertools import product
import useq

# to create a new CMMCorePlus() for every test
@pytest.fixture
def core(monkeypatch):
    new_core = CMMCorePlus()
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", new_core)
    return new_core


@pytest.fixture
def main_window(core: CMMCorePlus, make_napari_viewer):
    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer)
    assert core == win._mmc
    config_path = str(Path(__file__).parent / "test_config.cfg")
    win._mmc.loadSystemConfiguration(config_path)
    return win


TIME_PLANS = (None, useq.TIntervalLoops(loops=3, interval=0.250))
Z_PLANS = (None, useq.ZRangeAround(range=3, step=1))
CHANNEL_PLANS = (
    (useq.Channel(config="DAPI", exposure=5),),
    (useq.Channel(config="DAPI", exposure=5), useq.Channel(config="Cy5", exposure=5)),
)
MDAS = [
    {"time_plan": t, "z_plan": z, "channels": c}
    for t, z, c in itertools.product(TIME_PLANS, Z_PLANS, CHANNEL_PLANS)
]


@pytest.fixture(params=MDAS)
def mda_sequence(request) -> useq.MDASequence:
    meta = {SEQUENCE_META_KEY: SequenceMeta(mode="mda", file_name="test_mda")}
    return useq.MDASequence(**request.param, metadata=meta)


@pytest.fixture(params=[True, False])
def mda_sequence_splits(mda_sequence: useq.MDASequence, request) -> useq.MDASequence:
    if request.param:
        mda_sequence.metadata[SEQUENCE_META_KEY].split_channels = True
    return mda_sequence
import itertools
from pathlib import Path

import pytest
import useq
from napari_micromanager._util import NMM_METADATA_KEY
from napari_micromanager.main_window import MainWindow
from pymmcore_plus import CMMCorePlus


# to create a new CMMCorePlus() for every test
@pytest.fixture
def core(monkeypatch):
    new_core = CMMCorePlus()
    config_path = str(Path(__file__).parent / "test_config.cfg")
    new_core.loadSystemConfiguration(config_path)
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", new_core)
    return new_core


@pytest.fixture
def main_window(core: CMMCorePlus, make_napari_viewer):
    viewer = make_napari_viewer()
    win = MainWindow(viewer=viewer, init_configs=False)
    assert core == win._mmc
    return win


TIME_PLANS = (None, useq.TIntervalLoops(loops=3, interval=0.250))
Z_PLANS = (None, useq.ZRangeAround(range=3, step=0.5))
CHANNEL_PLANS = (
    (useq.Channel(config="DAPI", exposure=5),),
    (useq.Channel(config="DAPI", exposure=5), useq.Channel(config="Cy5", exposure=5)),
)
MDAS = [
    {"time_plan": t, "z_plan": z, "channels": c}
    for t, z, c in itertools.product(TIME_PLANS, Z_PLANS, CHANNEL_PLANS)
]
MDA_IDS = [
    f"nT={t}-nZ={z}-nC={len(c)}"
    for t, z, c in itertools.product((0, 3), (0, 7), CHANNEL_PLANS)
]


@pytest.fixture(params=MDAS, ids=MDA_IDS)
def mda_sequence(request: pytest.FixtureRequest) -> useq.MDASequence:
    return useq.MDASequence(
        **request.param, metadata={NMM_METADATA_KEY: {"split_channels": False}}
    )


@pytest.fixture(params=[True, False], ids=["splitC", "no_splitC"])
def mda_sequence_splits(mda_sequence: useq.MDASequence, request) -> useq.MDASequence:
    if request.param:
        meta = {"split_channels": True}
        mda_sequence.metadata[NMM_METADATA_KEY] = meta
    return mda_sequence

from __future__ import annotations

import itertools
import logging
import weakref
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import napari
import pytest
import useq
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.experimental.unicore import UniMMCore
from pymmcore_plus.experimental.unicore.core import _unicore

from napari_micromanager._util import NMM_METADATA_KEY
from napari_micromanager.main_window import MainWindow

if TYPE_CHECKING:
    from collections.abc import Iterator

# Prevent ipykernel debug logs from causing formatting errors in pytest
logging.getLogger("ipykernel.inprocess.ipkernel").setLevel(logging.ERROR)


@pytest.fixture(autouse=True)
def _smaller_default_buffer() -> Iterator[None]:
    """Reduce UniMMCore's default 1GB sequence buffer to avoid OOM on Windows CI."""
    with patch.object(_unicore, "_DEFAULT_BUFFER_SIZE_MB", 100):
        yield


_CORE_PARAMS = [
    pytest.param(CMMCorePlus, id="CMMCorePlus"),
    pytest.param(UniMMCore, id="UniMMCore"),
]


# to create a new CMMCorePlus/UniMMCore for every test
@pytest.fixture(params=_CORE_PARAMS)
def core(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> CMMCorePlus:
    new_core = request.param()
    config_path = str(Path(__file__).parent / "test_config.cfg")
    new_core.loadSystemConfiguration(config_path)
    monkeypatch.setattr(
        "pymmcore_plus.core._mmcore_plus._instance", weakref.ref(new_core)
    )
    return new_core


@pytest.fixture
def napari_viewer(qapp: Any) -> Iterator[napari.Viewer]:
    viewer = napari.Viewer(show=False)
    yield viewer
    with suppress(RuntimeError):
        viewer.close()


@pytest.fixture
def main_window(core: CMMCorePlus, napari_viewer: napari.Viewer) -> MainWindow:
    win = MainWindow(viewer=napari_viewer)
    napari_viewer.window.add_dock_widget(win, name="MainWindow")
    assert core == win._mmc
    return win


TIME_PLANS = (None, useq.TIntervalLoops(loops=3, interval=0))
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
def mda_sequence_splits(
    mda_sequence: useq.MDASequence, request: pytest.FixtureRequest
) -> useq.MDASequence:
    if request.param:
        meta = {"split_channels": True}
        mda_sequence.metadata[NMM_METADATA_KEY] = meta
    return mda_sequence

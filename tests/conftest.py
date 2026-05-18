from __future__ import annotations

import logging
import weakref
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import napari
import pytest
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.experimental.unicore import UniMMCore
from pymmcore_plus.experimental.unicore.core import _unicore

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
    win = MainWindow(viewer=napari_viewer, mmcore=core)
    napari_viewer.window.add_dock_widget(win, name="MainWindow")
    assert core == win._mmc
    return win

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


@pytest.fixture(autouse=True)
def _mock_pyconify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Mock pyconify.svg_path to avoid network requests in tests."""
    svg_dir = tmp_path / "icons"
    svg_dir.mkdir()
    _counter = 0

    def mock_svg_path(*key: str, color: str | None = None, **kwargs: object) -> Path:
        nonlocal _counter
        fill = color or "currentColor"
        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            f'<rect width="24" height="24" fill="{fill}"/></svg>'
        )
        svg_file = svg_dir / f"icon_{_counter}.svg"
        _counter += 1
        svg_file.write_text(svg_content)
        return svg_file

    monkeypatch.setattr("superqt.iconify.svg_path", mock_svg_path)
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

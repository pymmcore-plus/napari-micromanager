from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.experimental.unicore import UniMMCore

from napari_micromanager.main_window import MainWindow, get_core

if TYPE_CHECKING:
    import napari
    from pytestqt.qtbot import QtBot

CONFIG = str(Path(__file__).parent / "test_config.cfg")


@pytest.fixture
def mock_main_window(qtbot: QtBot, core: CMMCorePlus) -> MainWindow:
    viewer = MagicMock()
    win = MainWindow(viewer)
    qtbot.addWidget(win)
    return win


def test_set_core_updates_instance(mock_main_window: MainWindow) -> None:
    win = mock_main_window
    new_core = CMMCorePlus()
    new_core.loadSystemConfiguration(CONFIG)

    win.set_core(new_core)

    assert win.core is new_core
    assert win._mmc is new_core


def test_set_core_reconnects_core_link(mock_main_window: MainWindow) -> None:
    win = mock_main_window
    new_core = CMMCorePlus()
    new_core.loadSystemConfiguration(CONFIG)

    win.set_core(new_core)

    assert win._core_link._mmc is new_core
    assert win._core_link._mda_handler._mmc is new_core


def test_set_core_refuses_during_mda(mock_main_window: MainWindow) -> None:
    win = mock_main_window
    new_core = CMMCorePlus()

    # Simulate MDA running
    win._core_link._mda_handler._mda_running = True

    with pytest.raises(RuntimeError, match="Cannot swap core while MDA is running"):
        win.set_core(new_core)


def test_set_core_clears_dock_widgets(mock_main_window: MainWindow) -> None:
    win = mock_main_window

    # Fake a cached dock widget
    mock_dock = MagicMock()
    win._dock_widgets["test"] = mock_dock

    new_core = CMMCorePlus()
    new_core.loadSystemConfiguration(CONFIG)
    win.set_core(new_core)

    assert win._dock_widgets == {}
    mock_dock.close.assert_called_once()
    mock_dock.deleteLater.assert_called_once()


_SWAP_COMBOS = [
    pytest.param(CMMCorePlus, CMMCorePlus, id="CMMCorePlus->CMMCorePlus"),
    pytest.param(CMMCorePlus, UniMMCore, id="CMMCorePlus->UniMMCore"),
    pytest.param(UniMMCore, CMMCorePlus, id="UniMMCore->CMMCorePlus"),
    pytest.param(UniMMCore, UniMMCore, id="UniMMCore->UniMMCore"),
]


@pytest.mark.parametrize(("old_cls", "new_cls"), _SWAP_COMBOS)
def test_set_core_snap_uses_new_core(
    qtbot: QtBot,
    napari_viewer: napari.Viewer,
    monkeypatch: pytest.MonkeyPatch,
    old_cls: type,
    new_cls: type,
) -> None:
    """After set_core(), snap should come from the new core, not the old one."""
    old_core = old_cls()
    old_core.loadSystemConfiguration(CONFIG)
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", old_core)

    win = MainWindow(viewer=napari_viewer)
    qtbot.addWidget(win)
    assert win._mmc is old_core

    # Snap on old core (512x512 default)
    old_core.snap()
    win._core_link._image_snapped()
    assert "preview" in [lr.name for lr in napari_viewer.layers]
    old_data = napari_viewer.layers["preview"].data.copy()
    assert old_data.shape == (512, 512)

    # Create new core with a different camera size
    new_core = new_cls()
    new_core.loadSystemConfiguration(CONFIG)
    new_core.setProperty("Camera", "OnCameraCCDXSize", 128)
    new_core.setProperty("Camera", "OnCameraCCDYSize", 128)

    win.set_core(new_core)
    assert win._mmc is new_core
    assert win._core_link._mmc is new_core

    # Snap on new core
    new_core.snap()
    win._core_link._image_snapped()
    new_data = napari_viewer.layers["preview"].data

    # Image shape must reflect the new core's camera config
    assert new_data.shape == (128, 128), f"Expected (128, 128), got {new_data.shape}"


def test_set_core_during_live_mode(
    qtbot: QtBot,
    napari_viewer: napari.Viewer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching cores while live mode is running stops the old stream."""
    old_core = CMMCorePlus()
    old_core.loadSystemConfiguration(CONFIG)
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", old_core)

    win = MainWindow(viewer=napari_viewer)
    qtbot.addWidget(win)
    old_link = win._core_link

    # Start live mode
    old_core.startContinuousSequenceAcquisition()
    assert old_core.isSequenceRunning()
    assert old_link._live_timer_id is not None

    # Swap while live is running
    new_core = CMMCorePlus()
    new_core.loadSystemConfiguration(CONFIG)
    new_core.setProperty("Camera", "OnCameraCCDXSize", 128)
    new_core.setProperty("Camera", "OnCameraCCDYSize", 128)

    win.set_core(new_core)

    # Old live must be stopped
    assert not old_core.isSequenceRunning()
    assert old_link._live_timer_id is None

    # New core should work for snapping
    new_core.snap()
    win._core_link._image_snapped()
    assert napari_viewer.layers["preview"].data.shape == (128, 128)


def test_set_core_refused_during_real_mda(
    main_window: MainWindow, qtbot: QtBot
) -> None:
    """set_core() raises while an actual MDA is in progress, works after it ends."""
    import useq

    mmc = main_window._mmc
    seq = useq.MDASequence(
        time_plan={"loops": 3, "interval": 0.25},
        channels=["DAPI"],
    )

    new_core = CMMCorePlus()
    new_core.loadSystemConfiguration(CONFIG)

    # Start the MDA and wait for sequenceStarted so _mda_running is True
    with qtbot.waitSignal(mmc.mda.events.sequenceStarted, timeout=5000):
        mmc.run_mda(seq)

    assert main_window._core_link._mda_handler._mda_running

    # While running, set_core must refuse
    with pytest.raises(RuntimeError, match="Cannot swap core while MDA is running"):
        main_window.set_core(new_core)

    # Wait for MDA to finish
    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=5000):
        pass

    # After MDA finishes, swap should succeed
    main_window.set_core(new_core)
    assert main_window._mmc is new_core


# ---------------------------------------------------------------------------
# Auto-detect #py cfg tests
# ---------------------------------------------------------------------------


def _write_py_cfg(tmp_path: Path) -> str:
    """Write a minimal #py cfg and its Python module, return cfg path."""
    module_file = tmp_path / "minimal_devices.py"
    module_file.write_text(
        "from pymmcore_plus.experimental.unicore import ShutterDevice\n"
        "\n"
        "class MinimalShutter(ShutterDevice):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self._open = False\n"
        "    def get_open(self) -> bool:\n"
        "        return self._open\n"
        "    def set_open(self, open: bool) -> None:\n"
        "        self._open = open\n"
    )
    cfg_file = tmp_path / "py_devices.cfg"
    cfg_file.write_text(
        "#py pyDevice,Shutter,minimal_devices,MinimalShutter\n"
        "#py Property,Core,Shutter,Shutter\n"
        "#py Property,Core,Initialize,1\n"
    )
    return str(cfg_file)


def test_auto_detect_py_cfg_swaps_to_unicore(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CMMCorePlus + #py cfg → auto-swap to UniMMCore."""
    initial = CMMCorePlus()
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", initial)

    viewer = MagicMock()
    win = MainWindow(viewer)
    qtbot.addWidget(win)
    assert isinstance(win._mmc, CMMCorePlus)
    assert not isinstance(win._mmc, UniMMCore)

    py_cfg = _write_py_cfg(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        win._mmc.loadSystemConfiguration(py_cfg)
    finally:
        sys.path.remove(str(tmp_path))

    assert isinstance(win._mmc, UniMMCore)
    assert "Shutter" in win._mmc.getLoadedDevices()


def test_auto_detect_standard_cfg_swaps_to_mmcore(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UniMMCore + standard cfg → auto-swap to CMMCorePlus."""
    initial = UniMMCore()
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", initial)

    viewer = MagicMock()
    win = MainWindow(viewer)
    qtbot.addWidget(win)
    assert isinstance(win._mmc, UniMMCore)

    win._mmc.loadSystemConfiguration(CONFIG)

    assert type(win._mmc) is CMMCorePlus
    assert "Camera" in win._mmc.getLoadedDevices()


def test_auto_detect_no_swap_when_correct(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """UniMMCore + #py cfg → no swap, stays UniMMCore."""
    initial = UniMMCore()
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", initial)

    viewer = MagicMock()
    win = MainWindow(viewer)
    qtbot.addWidget(win)
    assert isinstance(win._mmc, UniMMCore)

    py_cfg = _write_py_cfg(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        win._mmc.loadSystemConfiguration(py_cfg)
    finally:
        sys.path.remove(str(tmp_path))

    # Same instance — no swap occurred
    assert win._mmc is initial
    assert "Shutter" in win._mmc.getLoadedDevices()


def test_auto_detect_file_not_found(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nonexistent cfg → no swap, error from core's loadSystemConfiguration."""
    initial = CMMCorePlus()
    monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", initial)

    viewer = MagicMock()
    win = MainWindow(viewer)
    qtbot.addWidget(win)

    with pytest.raises(FileNotFoundError):
        win._mmc.loadSystemConfiguration("/nonexistent/path.cfg")


# ---------------------------------------------------------------------------
# get_core tests
# ---------------------------------------------------------------------------


def test_get_core_returns_current(main_window: MainWindow) -> None:
    assert get_core() is main_window.core


def test_get_core_after_swap(main_window: MainWindow) -> None:
    new_core = CMMCorePlus()
    new_core.loadSystemConfiguration(CONFIG)
    main_window.set_core(new_core)

    assert get_core() is new_core

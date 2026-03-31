from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from pathlib import Path

    from pytestqt.qtbot import QtBot


def test_set_core_to_unicore(qtbot: QtBot) -> None:
    """set_core() swaps to UniMMCore after construction."""
    from pymmcore_plus.experimental.unicore import UniMMCore

    from napari_micromanager.main_window import MainWindow

    viewer = MagicMock()
    win = MainWindow(viewer)
    qtbot.addWidget(win)

    uni = UniMMCore()
    win.set_core(uni)

    assert win.core is uni
    assert isinstance(win.core, UniMMCore)

    win._cleanup()


def test_load_py_device_cfg(tmp_path: Path) -> None:
    """UniMMCore can load a cfg with #py pyDevice lines."""
    from pymmcore_plus.experimental.unicore import UniMMCore

    # Write a minimal shutter device that UniMMCore can import
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

    cfg_file = tmp_path / "minimal.cfg"
    cfg_file.write_text(
        "#py pyDevice,Shutter,minimal_devices,MinimalShutter\n"
        "#py Property,Core,Shutter,Shutter\n"
        "#py Property,Core,Initialize,1\n"
    )

    sys.path.insert(0, str(tmp_path))
    try:
        core = UniMMCore()
        core.loadSystemConfiguration(str(cfg_file))
        assert "Shutter" in core.getLoadedDevices()
    finally:
        sys.path.remove(str(tmp_path))

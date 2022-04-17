from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import DeviceType

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_shutter_widget(qtbot: QtBot, global_mmcore: CMMCorePlus):

    print(global_mmcore.getLoadedDevicesOfType(DeviceType.ShutterDevice))

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pymmcore_plus import CMMCorePlus

from micromanager_gui._core_widgets import DefaultCameraExposureWidget

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

# not sure how else to parametrize the test without instantiating here at import ...
CORE = CMMCorePlus()
CORE.loadSystemConfiguration(Path(__file__).parent.parent / "test_config.cfg")


def test_exposure_widget(qtbot: QtBot):
    CORE.setExposure(15)
    wdg = DefaultCameraExposureWidget(core=CORE)
    qtbot.addWidget(wdg)

    # check that it get's whatever core is set to.
    assert wdg.spinBox.value() == 15
    with qtbot.waitSignal(CORE.events.exposureChanged):
        CORE.setExposure(30)
    assert wdg.spinBox.value() == 30

    with qtbot.wait_signal(CORE.events.exposureChanged):
        wdg.spinBox.setValue(45)
    assert CORE.getExposure() == 45

    # test updating cameraDevice
    CORE.setProperty("Core", "Camera", "")
    assert not wdg.isEnabled()

    with pytest.raises(RuntimeError):
        wdg.setCamera("blarg")

    # set to an invalid camera name
    # should now be disabled.
    wdg.setCamera("blarg", force=True)
    assert not wdg.isEnabled()

    # reset the camera to a working one
    CORE.setProperty("Core", "Camera", "Camera")
    with qtbot.wait_signal(CORE.events.exposureChanged):
        wdg.spinBox.setValue(12)
    assert CORE.getExposure() == 12

from __future__ import annotations

from typing import TYPE_CHECKING

from micromanager_gui._core_widgets._snap_button_widget import SnapButton

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_snap_button_widget(qtbot: QtBot, global_mmcore: CMMCorePlus):

    snap_btn = SnapButton(
        button_text="Snap",
        icon_size=40,
        icon_color="green",
    )

    qtbot.addWidget(snap_btn)

    assert snap_btn.text() == "Snap"
    assert snap_btn.icon_size == 40
    assert snap_btn.icon_color == "green"

    global_mmcore.startContinuousSequenceAcquisition(0)

    with qtbot.waitSignals(
        [
            global_mmcore.events.stopSequenceAcquisition,
            global_mmcore.events.imageSnapped,
        ]
    ):
        snap_btn.click()
        assert not global_mmcore.isSequenceRunning()

from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_widgets._live_button_widget import LiveButton

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_live_button_widget(qtbot: QtBot, global_mmcore: CMMCorePlus):

    live_btn = LiveButton(
        button_text_on_off=("Live", "Stop"),
        icon_size=40,
        icon_color_on_off=("green", "magenta"),
    )

    qtbot.addWidget(live_btn)

    assert live_btn.text() == "Live"
    assert live_btn.icon_size == 40
    assert live_btn.icon_color_on == "green"
    assert live_btn.icon_color_off == "magenta"

    # test from direct mmcore signals
    with qtbot.waitSignal(global_mmcore.events.startContinuousSequenceAcquisition):
        global_mmcore.startContinuousSequenceAcquisition(0)
    assert live_btn.text() == "Stop"

    with qtbot.waitSignal(global_mmcore.events.stopSequenceAcquisition):
        global_mmcore.stopSequenceAcquisition()
    assert not global_mmcore.isSequenceRunning()
    assert live_btn.text() == "Live"

    # test when button is pressed
    with qtbot.waitSignal(global_mmcore.events.startContinuousSequenceAcquisition):
        live_btn.click()
    assert live_btn.text() == "Stop"
    assert global_mmcore.isSequenceRunning()

    with qtbot.waitSignal(global_mmcore.events.stopSequenceAcquisition):
        live_btn.click()
    assert not global_mmcore.isSequenceRunning()
    assert live_btn.text() == "Live"

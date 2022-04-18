from __future__ import annotations

from typing import TYPE_CHECKING

from micromanager_gui._core_widgets._shutter_widget import ShuttersWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_shutter_widget(qtbot: QtBot, global_mmcore: CMMCorePlus):

    shutter = ShuttersWidget(
        "Shutter",
        button_text_open_closed=("Shutter opened", "Shutter closed"),
        icon_color_open_closed=((0, 255, 0), "magenta"),
        autoshutter=False,
    )

    multi_shutter = ShuttersWidget(
        "Multi Shutter",
        button_text_open_closed=("Multi Shutter opened", "Multi Shutter closed"),
        icon_color_open_closed=((0, 255, 0), "magenta"),
    )

    qtbot.addWidget(shutter)
    qtbot.addWidget(multi_shutter)

    assert shutter.shutter_button.text() == "Shutter closed"
    assert not shutter.shutter_button.isEnabled()
    assert multi_shutter.shutter_button.text() == "Multi Shutter closed"
    assert multi_shutter.autoshutter_checkbox.isChecked()
    assert not multi_shutter.shutter_button.isEnabled()

    # test shutter change from core
    with qtbot.waitSignal(global_mmcore.events.autoShutterSet):
        global_mmcore.setAutoShutter(False)
        assert shutter.shutter_button.isEnabled()
        assert multi_shutter.shutter_button.isEnabled()

    with qtbot.waitSignal(global_mmcore.events.shutterSet):
        global_mmcore.setShutterOpen("Shutter", True)
        assert shutter.shutter_button.text() == "Shutter opened"
        global_mmcore.setShutterOpen("Multi Shutter", True)
        assert multi_shutter.shutter_button.text() == "Multi Shutter opened"

    with qtbot.waitSignal(global_mmcore.events.autoShutterSet):
        global_mmcore.setAutoShutter(True)
        assert not shutter.shutter_button.isEnabled()
        assert not multi_shutter.shutter_button.isEnabled()

    # test shutter change from shutter button
    with qtbot.waitSignal(global_mmcore.events.autoShutterSet):
        multi_shutter.autoshutter_checkbox.setChecked(False)
        assert shutter.shutter_button.isEnabled()
        assert multi_shutter.shutter_button.isEnabled()

    with qtbot.waitSignal(global_mmcore.events.shutterSet):
        shutter.shutter_button.click()
        assert shutter.shutter_button.text() == "Shutter opened"
        assert global_mmcore.getShutterOpen("Shutter")
        multi_shutter.shutter_button.click()
        assert multi_shutter.shutter_button.text() == "Multi Shutter opened"
        assert global_mmcore.getShutterOpen("Multi Shutter")

    # test autoshutter checkbox closing all shutters if checked
    assert global_mmcore.getShutterOpen("Shutter")
    assert global_mmcore.getShutterOpen("Multi Shutter")
    with qtbot.waitSignal(global_mmcore.events.autoShutterSet):
        global_mmcore.setAutoShutter(True)
        assert not global_mmcore.getShutterOpen("Shutter")
        assert not global_mmcore.getShutterOpen("Multi Shutter")
        assert not shutter.shutter_button.isEnabled()
        assert not multi_shutter.shutter_button.isEnabled()

    # test link shutter and multi shutter
    global_mmcore.setConfig("Channel", "FITC")
    assert not global_mmcore.getShutterOpen("Shutter")
    assert not global_mmcore.getShutterOpen("Multi Shutter")
    with qtbot.waitSignal(global_mmcore.events.autoShutterSet):
        global_mmcore.setAutoShutter(False)
        with qtbot.waitSignal(global_mmcore.events.shutterSet):
            multi_shutter.shutter_button.click()
            assert global_mmcore.getShutterOpen("Shutter")
            assert global_mmcore.getShutterOpen("Multi Shutter")

    # assert live_btn.text() == "Live"
    # assert live_btn.icon_size == 40
    # assert live_btn.icon_color_on == "green"
    # assert live_btn.icon_color_off == "magenta"

    # # test from direct mmcore signals
    # with qtbot.waitSignal(global_mmcore.events.startContinuousSequenceAcquisition):
    #     global_mmcore.startContinuousSequenceAcquisition(0)
    #     assert live_btn.text() == "Stop"

    # with qtbot.waitSignal(global_mmcore.events.stopSequenceAcquisition):
    #     global_mmcore.stopSequenceAcquisition()
    #     assert not global_mmcore.isSequenceRunning()
    #     assert live_btn.text() == "Live"

    # # test when button is pressed
    # with qtbot.waitSignal(global_mmcore.events.startContinuousSequenceAcquisition):
    #     live_btn.click()
    #     assert live_btn.text() == "Stop"
    #     assert global_mmcore.isSequenceRunning()

    # with qtbot.waitSignal(global_mmcore.events.stopSequenceAcquisition):
    #     live_btn.click()
    #     assert not global_mmcore.isSequenceRunning()
    #     assert live_btn.text() == "Live"

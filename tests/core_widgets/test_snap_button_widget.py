from micromanager_gui._core_widgets._snap_button_widget import SnapButton


def test_snap_button_widget(qtbot, global_mmcore):

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

    snap_btn.click()

    assert not global_mmcore.isSequenceRunning()

    with qtbot.waitSignal(global_mmcore.events.imageSnapped) as image:
        assert image

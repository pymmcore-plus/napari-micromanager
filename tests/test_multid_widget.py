from useq import MDASequence

from micromanager_gui.multid_widget import MultiDWidget


def test_multid_load_state(qtbot, global_mmcore):
    wdg = MultiDWidget(global_mmcore)
    qtbot.addWidget(wdg)
    assert wdg.stage_tableWidget.rowCount() == 0
    assert wdg.channel_tableWidget.rowCount() == 0
    assert not wdg.time_groupBox.isChecked()
    sequence = MDASequence(
        channels=["Cy5", {"config": "FITC", "exposure": 50}],
        time_plan={"interval": 2, "loops": 5},
        z_plan={"range": 4, "step": 0.5},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
    )
    wdg.set_state(sequence)
    assert wdg.stage_tableWidget.rowCount() == 2
    assert wdg.channel_tableWidget.rowCount() == 2
    assert wdg.time_groupBox.isChecked()

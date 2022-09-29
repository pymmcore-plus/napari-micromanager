from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from useq import MDASequence

from micromanager_gui._gui_objects._mda_widget import MDAWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


def test_multid_load_state(qtbot: QtBot, core: CMMCorePlus):
    wdg = MDAWidget()
    config_path = str(Path(__file__).parent / "test_config.cfg")
    wdg._mmc.loadSystemConfiguration(config_path)
    qtbot.addWidget(wdg)
    assert wdg.stage_tableWidget.rowCount() == 0
    assert wdg.channel_tableWidget.rowCount() == 0
    assert not wdg.time_groupBox.isChecked()
    sequence = MDASequence(
        channels=[
            {"config": "Cy5", "exposure": 20},
            {"config": "FITC", "exposure": 50},
        ],
        time_plan={"interval": 2, "loops": 5},
        z_plan={"range": 4, "step": 0.5},
        axis_order="tpcz",
        stage_positions=[
            {"x": 222, "y": 1, "z": 1, "name": "Pos000"},
            {"x": 111, "y": 0, "z": 0, "name": "Pos001"},
        ],
    )
    wdg.set_state(sequence)
    assert wdg.stage_tableWidget.rowCount() == 2
    assert wdg.channel_tableWidget.rowCount() == 2
    assert wdg.time_groupBox.isChecked()

    # round trip
    assert wdg._get_state() == sequence

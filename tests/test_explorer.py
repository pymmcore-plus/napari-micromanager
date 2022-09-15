from __future__ import annotations

from typing import TYPE_CHECKING

from micromanager_gui import _mda
from micromanager_gui.main_window import MainWindow

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from useq import MDASequence


def test_explorer(qtbot: QtBot, main_window: MainWindow):
    # sourcery skip: remove-duplicate-set-key

    s_exp = main_window.explorer
    qtbot.add_widget(s_exp)
    mmc = main_window._mmc

    assert len(s_exp._mmc.getLoadedDevices()) > 2
    assert mmc.getChannelGroup() == "Channel"

    s_exp.scan_size_spinBox_c.setValue(2)
    s_exp.scan_size_spinBox_r.setValue(2)
    s_exp.ovelap_spinBox.setValue(10)

    s_exp.add_ch_explorer_Button.click()
    assert s_exp.channel_explorer_tableWidget.rowCount() == 1

    s_exp.time_groupBox.setChecked(True)
    s_exp.timepoints_spinBox.setValue(2)
    s_exp.interval_spinBox.setValue(0)

    s_exp.stack_groupBox.setChecked(True)
    s_exp.z_tabWidget.setCurrentIndex(1)
    s_exp.zrange_spinBox.setValue(2)
    s_exp.step_size_doubleSpinBox.setValue(1.0)
    assert s_exp.n_images_label.text() == "Number of Images: 3"

    s_exp.stage_pos_groupBox.setChecked(True)
    s_exp.add_pos_Button.click()
    assert s_exp.stage_tableWidget.rowCount() == 1
    mmc.setXYPosition(2000.0, 2000.0)
    mmc.waitForSystem()
    s_exp.add_pos_Button.click()

    assert s_exp.stage_tableWidget.rowCount() == 2

    state = s_exp._get_state_dict()

    assert state["channels"] == [
        {
            "config": "Cy5",
            "group": "Channel",
            "exposure": 100,
        }
    ]

    assert state["stage_positions"] == [
        {"name": "Grid_000_Pos000", "x": -307.2, "y": 307.2, "z": 0.0},
        {"name": "Grid_000_Pos001", "x": 153.60000000000002, "y": 307.2, "z": 0.0},
        {
            "name": "Grid_000_Pos002",
            "x": 153.60000000000002,
            "y": -153.60000000000002,
            "z": 0.0,
        },
        {"name": "Grid_000_Pos003", "x": -307.2, "y": -153.60000000000002, "z": 0.0},
        {
            "name": "Grid_001_Pos000",
            "x": 1692.7949999999998,
            "y": 2307.1949999999997,
            "z": 0.0,
        },
        {"name": "Grid_001_Pos001", "x": 2153.595, "y": 2307.1949999999997, "z": 0.0},
        {"name": "Grid_001_Pos002", "x": 2153.595, "y": 1846.3949999999998, "z": 0.0},
        {
            "name": "Grid_001_Pos003",
            "x": 1692.7949999999998,
            "y": 1846.3949999999998,
            "z": 0.0,
        },
    ]

    assert state["time_plan"] == {"interval": {"milliseconds": 0}, "loops": 2}

    assert state["z_plan"] == {
        "range": 2,
        "step": 1,
    }

    # grab these in callback so we get the real meta that is
    # created once we start the scan
    sequence = None
    meta = None

    @mmc.mda.events.sequenceStarted.connect
    def get_seq(seq: MDASequence):
        nonlocal sequence, meta
        sequence = seq
        meta = _mda.SEQUENCE_META[seq]

    with qtbot.waitSignals(
        [mmc.mda.events.sequenceStarted, mmc.mda.events.sequenceFinished], timeout=15000
    ):
        s_exp._start_scan()

    assert meta
    assert meta.mode == "explorer"
    assert meta.should_save == s_exp.save_explorer_groupBox.isChecked()
    assert meta.translate_explorer
    assert not meta.translate_explorer_real_coords
    assert meta.explorer_translation_points == [
        (-256.0, 256.0, 0, 0),
        (204.8, 256.0, 0, 1),
        (204.8, -204.8, 1, 0),
        (-256.0, -204.8, 1, 1),
        (-256.0, 256.0, 0, 0),
        (204.8, 256.0, 0, 1),
        (204.8, -204.8, 1, 0),
        (-256.0, -204.8, 1, 1),
    ]


# TODO: add test_saving_explorer

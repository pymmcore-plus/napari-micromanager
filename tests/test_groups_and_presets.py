from micromanager_gui.main_window import MainWindow


def test_groups_and_presets(main_window: MainWindow):

    assert main_window.tabWidget.count() == 4

    obj_cfg = main_window.objectives_cfg
    assert obj_cfg == "Objective"
    assert list(main_window._mmc.getAvailableConfigs(obj_cfg)) == ["10X", "20X", "40X"]

    channel_group = main_window._mmc.getOrGuessChannelGroup()
    assert channel_group == ["Channel"]
    assert len(channel_group) == 1
    assert channel_group[0] == "Channel"

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb
    assert mm_table

from micromanager_gui.main_window import MainWindow


def test_table_objective_and_channel_comboboxes(main_window: MainWindow):

    assert main_window.tabWidget.count() == 4
    assert main_window.tabWidget.currentIndex() == 0
    assert main_window.tabWidget.tabText(0) == "Groups and Presets"

    channel_group = main_window._mmc.getOrGuessChannelGroup()
    assert channel_group == ["Channel"]
    assert len(channel_group) == 1
    assert channel_group[0] == "Channel"
    assert list(main_window._mmc.getAvailableConfigs(channel_group[0])) == [
        "Cy5",
        "DAPI",
        "FITC",
        "Rhodamine",
    ]

    obj_cfg = main_window.objectives_cfg
    assert obj_cfg == "Objective"
    assert list(main_window._mmc.getAvailableConfigs(obj_cfg)) == ["10X", "20X", "40X"]

    mm_table = main_window.groups_and_presets.tb
    assert mm_table.native.rowCount() == 5
    assert mm_table.native.columnCount() == 2

    # test channel comboboxes
    # set channel_tab_cbox to "Rhodamine" -> it should change also snap_channel_comboBox
    _, channel_tab_cbox = mm_table.data[1]  # channel combobox in table
    channel_tab_cbox.value = "Rhodamine"
    assert main_window.snap_channel_comboBox.currentText() == "Rhodamine"
    assert channel_tab_cbox.get_value() == "Rhodamine"

    # set snap_channel_comboBox to "DAPI" -> it should change also channel_tab_cbox
    main_window.snap_channel_comboBox.setCurrentText("DAPI")
    assert channel_tab_cbox.get_value() == "DAPI"
    assert main_window.snap_channel_comboBox.currentText() == "DAPI"

    # test objective comboboxes
    # set objective_tab_cbox to "20X" -> it should change also objective_comboBox
    _, objective_tab_cbox = mm_table.data[3]
    objective_tab_cbox.value = "20X"
    assert main_window.objective_comboBox.currentText() == "20X"
    assert objective_tab_cbox.get_value() == "20X"

    # set objective_comboBox to "40X" -> it should change also objective_tab_cbox
    main_window.objective_comboBox.setCurrentText("40X")
    assert objective_tab_cbox.get_value() == "40X"
    assert main_window.objective_comboBox.currentText() == "40X"


def test_delete_group(main_window: MainWindow):
    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb
    assert mm_table.native.rowCount() == 5

    objective_group, _ = mm_table.data[3]
    assert objective_group == "Objective"

    mm_table.native.setCurrentCell(3, 0)
    gp_ps._delete_selected_group()

    assert mm_table.native.rowCount() == 4
    assert not list(main_window._mmc.getAvailableConfigs(objective_group))
    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]
    objective_comboBox_items.sort()
    assert objective_comboBox_items[0] == "Nikon 10X S Fluor"

    channel_group, _ = mm_table.data[1]
    assert channel_group == "Channel"

    mm_table.native.setCurrentCell(1, 0)
    gp_ps._delete_selected_group()

    assert mm_table.native.rowCount() == 3
    assert main_window._mmc.getOrGuessChannelGroup() == []
    snap_channel_comboBox_items = [
        main_window.snap_channel_comboBox.itemText(i)
        for i in range(main_window.snap_channel_comboBox.count())
    ]
    assert not snap_channel_comboBox_items


def test_delete_preset(main_window: MainWindow):

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb
    assert mm_table.native.rowCount() == 5

    objective_group, objective_tab_cbox = mm_table.data[3]
    objective_tab_cbox_items = [
        objective_tab_cbox.native.itemText(i)
        for i in range(objective_tab_cbox.native.count())
    ]
    assert objective_group == "Objective"
    assert objective_tab_cbox_items == ["10X", "20X", "40X"]
    assert (
        list(main_window._mmc.getAvailableConfigs(objective_group))
        == objective_tab_cbox_items
    )

    objective_tab_cbox.value = "40X"
    # main_window._mmc.events.configSet.emit("Objective", "40X")  # FOR REMOTE????
    mm_table.native.setCurrentCell(3, 0)
    gp_ps._delete_selected_preset()

    assert mm_table.native.rowCount() == 5
    assert list(main_window._mmc.getAvailableConfigs(objective_group)) == ["10X", "20X"]
    objective_tab_cbox_items = [
        objective_tab_cbox.native.itemText(i)
        for i in range(objective_tab_cbox.native.count())
    ]
    assert objective_tab_cbox_items == ["10X", "20X"]
    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]
    assert objective_comboBox_items == ["10X", "20X"]


# def test_groups_and_presets_edit(main_window: MainWindow):
# # test edit

# def test_groups_and_presets_rename(main_window: MainWindow):
# # test rename

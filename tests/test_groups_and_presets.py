from qtpy.QtCore import Qt

from micromanager_gui._properties_table_with_checkbox import GroupConfigurations
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
    objective_tab_cbox_items = objective_tab_cbox.choices
    assert objective_group == "Objective"
    assert list(objective_tab_cbox_items) == ["10X", "20X", "40X"]
    assert list(main_window._mmc.getAvailableConfigs(objective_group)) == list(
        objective_tab_cbox_items
    )

    objective_tab_cbox.value = "40X"
    # main_window._mmc.events.configSet.emit("Objective", "40X")  # FOR REMOTE????
    mm_table.native.setCurrentCell(3, 0)
    gp_ps._delete_selected_preset()

    assert mm_table.native.rowCount() == 5
    assert list(main_window._mmc.getAvailableConfigs(objective_group)) == ["10X", "20X"]

    objective_tab_cbox_items = objective_tab_cbox.choices
    assert list(objective_tab_cbox_items) == ["10X", "20X"]
    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]
    assert objective_comboBox_items == ["10X", "20X"]


# def test_groups_and_presets_rename(main_window: MainWindow):
#     pass


def test_groups_and_presets_edit_add_prop(main_window: MainWindow):

    dev_prop_val = main_window.dict_group_presets_table["Objective"]["20X"].get(
        "dev_prop_val"
    )[0]
    assert dev_prop_val == [("Objective", "State", "3")]

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb
    assert mm_table.native.rowCount() == 5

    _, objective_tab_cbox = mm_table.data[3]

    objective_tab_cbox.value = "20X"
    assert objective_tab_cbox.get_value() == "20X"

    mm_table.native.setCurrentCell(3, 0)
    assert mm_table.native.currentRow() == 3

    cfg_wdg = GroupConfigurations(main_window._mmc)

    cfg_wdg._reset_comboboxes()

    group, preset, _to_find, _to_find_list = gp_ps._edit_selected_group_preset()

    cfg_wdg._set_checkboxes_status(group, preset, _to_find, _to_find_list)

    matching_items = cfg_wdg.pt.native.findItems("Objective-State", Qt.MatchContains)
    row = matching_items[0].row()

    checkbox = cfg_wdg.pt.data[row, 1]
    assert checkbox.value
    state_wdg = cfg_wdg.pt.data[row, 3]
    assert state_wdg.value == "3"

    matching_items = cfg_wdg.pt.native.findItems("Objective-Label", Qt.MatchContains)
    row = matching_items[0].row()
    checkbox = cfg_wdg.pt.data[row, 1]
    checkbox.value = True

    total_true = 0
    for r in range(cfg_wdg.pt.shape[0]):
        _, combobox, _, _ = cfg_wdg.pt.data[r]
        if combobox.value:
            total_true += 1

    assert total_true == 2

    assert cfg_wdg.group_le.value == "Objective"
    assert cfg_wdg.preset_le.value == "20X"

    label_wdg = cfg_wdg.pt.data[row, 3]
    assert label_wdg.value == "Nikon 20X Plan Fluor ELWD"

    cfg_wdg.new_group_preset.connect(main_window._update_group_preset_table_edit)
    cfg_wdg._create_group_and_preset()

    k_list_20x = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Objective", "20X")
    ]

    assert ("Objective", "State", "3") in k_list_20x
    assert ("Objective", "Label", "Nikon 20X Plan Fluor ELWD") in k_list_20x

    k_list_10x = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Objective", "10X")
    ]
    assert ("Objective", "State", "1") in k_list_10x
    assert ("Objective", "Label", "Nikon 20X Plan Fluor ELWD") in k_list_10x


def test_groups_and_presets_edit_remove_prop(main_window: MainWindow):

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    _, objective_tab_cbox = mm_table.data[3]

    objective_tab_cbox.value = "20X"
    assert objective_tab_cbox.get_value() == "20X"

    mm_table.native.setCurrentCell(3, 0)
    assert mm_table.native.currentRow() == 3

    cfg_wdg = GroupConfigurations(main_window._mmc)

    cfg_wdg._reset_comboboxes()

    group, preset, _to_find, _to_find_list = gp_ps._edit_selected_group_preset()

    cfg_wdg._set_checkboxes_status(group, preset, _to_find, _to_find_list)

    matching_items = cfg_wdg.pt.native.findItems("Objective-State", Qt.MatchContains)
    row = matching_items[0].row()

    state_checkbox = cfg_wdg.pt.data[row, 1]
    assert state_checkbox.value
    state_wdg = cfg_wdg.pt.data[row, 3]
    assert state_wdg.value == "3"

    state_checkbox.value = False
    assert not state_checkbox.value

    matching_items = cfg_wdg.pt.native.findItems("Objective-Label", Qt.MatchContains)
    row = matching_items[0].row()
    label_checkbox = cfg_wdg.pt.data[row, 1]
    label_checkbox.value = True

    total = []
    for r in range(cfg_wdg.pt.shape[0]):
        _, checkbox, dev_prop, _ = cfg_wdg.pt.data[r]
        if checkbox.value:
            total.append(dev_prop)

    assert len(total) == 1
    assert total[0] == "Objective-Label"

    assert cfg_wdg.group_le.value == "Objective"
    assert cfg_wdg.preset_le.value == "20X"

    label_wdg = cfg_wdg.pt.data[row, 3]
    assert label_wdg.value == "Nikon 20X Plan Fluor ELWD"

    cfg_wdg.new_group_preset.connect(main_window._update_group_preset_table_edit)
    cfg_wdg._create_group_and_preset()

    k_list_20x = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Objective", "20X")
    ]
    assert ("Objective", "State", "3") not in k_list_20x
    assert ("Objective", "Label", "Nikon 20X Plan Fluor ELWD") in k_list_20x

    k_list_10x = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Objective", "10X")
    ]
    assert ("Objective", "State", "1") not in k_list_10x
    assert ("Objective", "Label", "Nikon 20X Plan Fluor ELWD") in k_list_10x

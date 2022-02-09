from magicgui.widgets import ComboBox, FloatSlider
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


def test_add_group_combobox_obj(main_window: MainWindow):

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    # delete current objectives group
    objective_group, _ = mm_table.data[3]
    assert objective_group == "Objective"
    mm_table.native.setCurrentCell(3, 0)
    gp_ps.delete_gp_btn.native.click()
    assert "Objective" not in main_window._mmc.getAvailableConfigGroups()

    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]
    assert "Nikon 10X S Fluor" in objective_comboBox_items

    # add a new objectives group
    create_wdg = GroupConfigurations(main_window._mmc)
    create_wdg.new_group_preset.connect(main_window._update_group_preset_table)
    create_wdg._reset_comboboxes()

    matching_items = create_wdg.pt.native.findItems("Objective-Label", Qt.MatchContains)
    row = matching_items[0].row()

    checkbox = create_wdg.pt.data[row, 1]
    checkbox.value = True
    assert checkbox.value
    wdg = create_wdg.pt.data[row, 3]
    wdg.value = "Nikon 10X S Fluor"
    assert wdg.value == "Nikon 10X S Fluor"

    total_true = 0
    for r in range(create_wdg.pt.shape[0]):
        _, combobox, _, _ = create_wdg.pt.data[r]
        if combobox.value:
            total_true += 1

    assert total_true == 1

    create_wdg.group_le.value = "Objectives"
    create_wdg.preset_le.value = "10X"

    create_wdg.create_btn.native.click()

    assert "Objectives" in main_window._mmc.getAvailableConfigGroups()

    dev_prop_val = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Objectives", "10X")
    ]

    assert len(dev_prop_val) == 1
    assert ("Objective", "Label", "Nikon 10X S Fluor") in dev_prop_val

    # add a second preset to the same group
    wdg.value = "Nikon 20X Plan Fluor ELWD"
    assert wdg.value == "Nikon 20X Plan Fluor ELWD"

    create_wdg.group_le.value = "Objectives"
    create_wdg.preset_le.value = "20X"

    create_wdg.create_btn.native.click()

    row = mm_table.native.rowCount()
    objective_group, objective_tab_cbox = mm_table.data[row - 1]
    assert objective_group == "Objectives"
    assert type(objective_tab_cbox) == ComboBox

    assert "Objectives" in main_window._mmc.getAvailableConfigGroups()

    obj_1 = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Objectives", "10X")
    ]
    obj_2 = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Objectives", "20X")
    ]

    assert len(obj_1) == 1
    assert len(obj_2) == 1
    assert ("Objective", "Label", "Nikon 10X S Fluor") in obj_1
    assert ("Objective", "Label", "Nikon 20X Plan Fluor ELWD") in obj_2

    assert list(main_window._mmc.getAvailableConfigs("Objectives")) == list(
        objective_tab_cbox.choices
    )

    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]

    assert objective_comboBox_items == list(objective_tab_cbox.choices)

    objective_tab_cbox.value = "20X"
    assert (
        main_window._mmc.getProperty("Objective", "Label")
        == "Nikon 20X Plan Fluor ELWD"
    )

    objective_tab_cbox.value = "10X"
    assert main_window._mmc.getProperty("Objective", "Label") == "Nikon 10X S Fluor"


def test_add_group_combobox_ch(main_window: MainWindow):

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    assert main_window._mmc.getChannelGroup() == "Channel"

    # delete current channel group
    objective_group, _ = mm_table.data[1]
    assert objective_group == "Channel"
    mm_table.native.setCurrentCell(1, 0)
    gp_ps.delete_gp_btn.native.click()
    assert "Channel" not in main_window._mmc.getAvailableConfigGroups()
    assert main_window._mmc.getChannelGroup() == ""

    # add a new objectives group
    create_wdg = GroupConfigurations(main_window._mmc)
    create_wdg.new_group_preset.connect(main_window._update_group_preset_table)
    create_wdg._reset_comboboxes()

    matching_items = create_wdg.pt.native.findItems("Dichroic-Label", Qt.MatchContains)
    row = matching_items[0].row()

    checkbox = create_wdg.pt.data[row, 1]
    checkbox.value = True
    assert checkbox.value
    d_wdg = create_wdg.pt.data[row, 3]
    d_wdg.value = "400DCLP"
    assert d_wdg.value == "400DCLP"

    matching_items = create_wdg.pt.native.findItems("Camera-Mode", Qt.MatchContains)
    row = matching_items[0].row()

    checkbox1 = create_wdg.pt.data[row, 1]
    checkbox1.value = True
    assert checkbox1.value
    cam_wdg = create_wdg.pt.data[row, 3]
    cam_wdg.value = "Noise"
    assert cam_wdg.value == "Noise"

    total_true = 0
    for r in range(create_wdg.pt.shape[0]):
        _, combobox, _, _ = create_wdg.pt.data[r]
        if combobox.value:
            total_true += 1

    assert total_true == 2

    create_wdg.group_le.value = "Channels"
    create_wdg.preset_le.value = "DAPI"

    create_wdg.create_btn.native.click()

    assert "Channels" in main_window._mmc.getAvailableConfigGroups()

    dev_prop_val = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Channels", "DAPI")
    ]

    assert len(dev_prop_val) == 2
    assert ("Dichroic", "Label", "400DCLP") in dev_prop_val
    assert ("Camera", "Mode", "Noise") in dev_prop_val

    # add a second preset to the same group
    d_wdg.value = "Q505LP"
    assert d_wdg.value == "Q505LP"
    cam_wdg.value = "Artificial Waves"
    assert cam_wdg.value == "Artificial Waves"

    create_wdg.group_le.value = "Channels"
    create_wdg.preset_le.value = "FITC"

    create_wdg.create_btn.native.click()

    row = mm_table.native.rowCount()
    channel_group, channel_tab_cbox = mm_table.data[row - 1]
    assert channel_group == "Channels"
    assert type(channel_tab_cbox) == ComboBox

    assert "Channels" in main_window._mmc.getAvailableConfigGroups()

    ch_1 = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Channels", "DAPI")
    ]
    ch_2 = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Channels", "FITC")
    ]

    assert len(ch_1) == 2
    assert len(ch_2) == 2
    assert ("Dichroic", "Label", "400DCLP") in ch_1
    assert ("Camera", "Mode", "Noise") in ch_1
    assert ("Dichroic", "Label", "Q505LP") in ch_2
    assert ("Camera", "Mode", "Artificial Waves") in ch_2

    assert list(main_window._mmc.getAvailableConfigs("Channels")) == list(
        channel_tab_cbox.choices
    )

    snap_channel_comboBox_items = [
        main_window.snap_channel_comboBox.itemText(i)
        for i in range(main_window.snap_channel_comboBox.count())
    ]
    assert snap_channel_comboBox_items == list(channel_tab_cbox.choices)

    channel_tab_cbox.value = "FITC"
    assert main_window._mmc.getProperty("Dichroic", "Label") == "Q505LP"
    assert main_window._mmc.getProperty("Camera", "Mode") == "Artificial Waves"

    channel_tab_cbox.value = "DAPI"
    assert main_window._mmc.getProperty("Dichroic", "Label") == "400DCLP"
    assert main_window._mmc.getProperty("Camera", "Mode") == "Noise"


def test_add_group_slider(main_window: MainWindow):
    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    create_wdg = GroupConfigurations(main_window._mmc)
    create_wdg.new_group_preset.connect(main_window._update_group_preset_table)
    create_wdg._reset_comboboxes()

    matching_items = create_wdg.pt.native.findItems(
        "Camera-TestProperty1", Qt.MatchContains
    )
    row = matching_items[0].row()

    checkbox_1 = create_wdg.pt.data[row, 1]
    checkbox_1.value = True
    assert checkbox_1.value
    slider_wdg_1 = create_wdg.pt.data[row, 3]
    slider_wdg_1.value = 0.1
    assert slider_wdg_1.value == 0.1

    total_true = 0
    for r in range(create_wdg.pt.shape[0]):
        _, combobox, _, _ = create_wdg.pt.data[r]
        if combobox.value:
            total_true += 1

    assert total_true == 1

    create_wdg.group_le.value = "Test"
    create_wdg.preset_le.value = "Slider"

    create_wdg.create_btn.native.click()

    assert "Test" in main_window._mmc.getAvailableConfigGroups()

    dev_prop_val = [
        (k[0], k[1], k[2]) for k in main_window._mmc.getConfigData("Test", "Slider")
    ]

    assert len(dev_prop_val) == 1
    assert ("Camera", "TestProperty1", "0.1") in dev_prop_val

    row = mm_table.native.rowCount()
    group, wdg = mm_table.data[row - 1]
    assert group == "Test"
    assert type(wdg) == FloatSlider

    wdg.value = 0.1
    assert main_window._mmc.getProperty("Camera", "TestProperty1") == "0.1000"

    wdg.value = 0.0
    assert main_window._mmc.getProperty("Camera", "TestProperty1") == "0.0000"


def test_delete_group(main_window: MainWindow):
    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    # delete objective group
    objective_group, _ = mm_table.data[3]
    assert objective_group == "Objective"

    mm_table.native.setCurrentCell(3, 0)
    gp_ps.delete_gp_btn.native.click()

    assert mm_table.native.rowCount() == 4
    assert not list(main_window._mmc.getAvailableConfigs(objective_group))
    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]
    objective_comboBox_items.sort()
    # objective labels should be used in the objective_comboBox
    assert objective_comboBox_items[0] == "Nikon 10X S Fluor"

    # delete channel group
    channel_group, _ = mm_table.data[1]
    assert channel_group == "Channel"

    mm_table.native.setCurrentCell(1, 0)
    gp_ps.delete_gp_btn.native.click()

    assert mm_table.native.rowCount() == 3
    assert main_window._mmc.getOrGuessChannelGroup() == []
    snap_channel_comboBox_items = [
        main_window.snap_channel_comboBox.itemText(i)
        for i in range(main_window.snap_channel_comboBox.count())
    ]
    # there should not be a chennel group
    assert not snap_channel_comboBox_items


def test_delete_preset_ch(main_window: MainWindow):

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    # objective_group, objective_tab_cbox = mm_table.data[3]
    channel_group, channel_tab_cbox = mm_table.data[1]
    # objective_tab_cbox_items = objective_tab_cbox.choices
    channel_tab_cbox_items = channel_tab_cbox.choices
    assert channel_group == "Channel"
    assert list(channel_tab_cbox_items) == [
        "Cy5",
        "DAPI",
        "FITC",
        "Rhodamine",
    ]

    assert list(main_window._mmc.getAvailableConfigs(channel_group)) == list(
        channel_tab_cbox_items
    )

    channel_tab_cbox.value = "FITC"
    mm_table.native.setCurrentCell(1, 0)
    gp_ps.delete_ps_btn.native.click()

    assert mm_table.native.rowCount() == 5
    assert list(main_window._mmc.getAvailableConfigs(channel_group)) == [
        "Cy5",
        "DAPI",
        "Rhodamine",
    ]

    objective_tab_cbox_items = channel_tab_cbox.choices
    assert list(objective_tab_cbox_items) == [
        "Cy5",
        "DAPI",
        "Rhodamine",
    ]
    snap_channel_comboBox_items = [
        main_window.snap_channel_comboBox.itemText(i)
        for i in range(main_window.snap_channel_comboBox.count())
    ]
    assert snap_channel_comboBox_items == [
        "Cy5",
        "DAPI",
        "Rhodamine",
    ]


def test_delete_preset_obj(main_window: MainWindow):

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
    mm_table.native.setCurrentCell(3, 0)
    gp_ps.delete_ps_btn.native.click()

    assert mm_table.native.rowCount() == 5
    assert list(main_window._mmc.getAvailableConfigs(objective_group)) == ["10X", "20X"]

    objective_tab_cbox_items = objective_tab_cbox.choices
    assert list(objective_tab_cbox_items) == ["10X", "20X"]
    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]
    assert objective_comboBox_items == ["10X", "20X"]


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
    cfg_wdg.create_btn.native.click()

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
    cfg_wdg.create_btn.native.click()

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


def test_groups_and_presets_rename_obj(main_window: MainWindow):

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    mm_table.native.setCurrentCell(3, 0)

    _, objective_tab_cbox = mm_table.data[3]

    objective_tab_cbox.value = "40X"
    assert objective_tab_cbox.get_value() == "40X"

    main_window.old_g, main_window.old_p = main_window._populate_rename_widget(mm_table)

    assert main_window.old_g == "Objective"
    assert main_window.old_p == "40X"

    main_window._rw.gp_lineedit.value = "Obj"
    main_window._rw.ps_lineedit.value = "40X Air"

    main_window._rename_group_preset()

    assert "Objective" not in main_window._mmc.getAvailableConfigGroups()
    assert "Obj" in main_window._mmc.getAvailableConfigGroups()

    assert list(main_window._mmc.getAvailableConfigs("Obj")) == [
        "10X",
        "20X",
        "40X Air",
    ]

    objective_comboBox_items = [
        main_window.objective_comboBox.itemText(i)
        for i in range(main_window.objective_comboBox.count())
    ]
    assert main_window.objectives_cfg == "Obj"
    assert list(main_window._mmc.getAvailableConfigs("Obj")) == objective_comboBox_items

    _, objective_tab_cbox = mm_table.data[3]
    assert list(main_window._mmc.getAvailableConfigs("Obj")) == list(
        objective_tab_cbox.choices
    )


def test_groups_and_presets_rename_ch(main_window: MainWindow):

    gp_ps = main_window.groups_and_presets
    mm_table = gp_ps.tb

    mm_table.native.setCurrentCell(1, 0)

    channel_group, channel_tab_cbox = mm_table.data[1]
    assert channel_group == "Channel"

    channel_tab_cbox.value = "FITC"
    assert channel_tab_cbox.get_value() == "FITC"

    main_window.old_g, main_window.old_p = main_window._populate_rename_widget(mm_table)

    assert main_window.old_g == "Channel"
    assert main_window.old_p == "FITC"

    main_window._rw.gp_lineedit.value = "Ch"
    main_window._rw.ps_lineedit.value = "GFP"

    main_window._rename_group_preset()

    assert "Channel" not in main_window._mmc.getAvailableConfigGroups()
    assert "Ch" in main_window._mmc.getAvailableConfigGroups()

    assert list(main_window._mmc.getAvailableConfigs("Ch")) == [
        "Cy5",
        "DAPI",
        "GFP",
        "Rhodamine",
    ]

    snap_channel_comboBox_items = [
        main_window.snap_channel_comboBox.itemText(i)
        for i in range(main_window.snap_channel_comboBox.count())
    ]
    assert main_window._mmc.getChannelGroup() == "Ch"
    assert (
        list(main_window._mmc.getAvailableConfigs("Ch")) == snap_channel_comboBox_items
    )

    _, channel_tab_cbox = mm_table.data[1]
    assert list(main_window._mmc.getAvailableConfigs("Ch")) == list(
        channel_tab_cbox.choices
    )


def test_groups_and_presets_save_cfg(main_window: MainWindow):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)

        gp_ps = main_window.groups_and_presets
        mm_table = gp_ps.tb

        row = mm_table.native.rowCount()
        gp, _ = mm_table.data[row - 1]
        assert gp == "System"
        mm_table.native.setCurrentCell(row - 1, 0)
        gp_ps.delete_gp_btn.native.click()

        assert mm_table.native.rowCount() == 4

        save_path = tmp_path / "new_cfg"
        main_window._save_cfg(save_path)

        assert [p.name for p in tmp_path.iterdir()] == ["new_cfg.cfg"]

        main_window._mmc.unloadAllDevices()
        main_window._mmc.loadSystemConfiguration(f"{tmp_path}/new_cfg.cfg")

        assert "System" not in main_window._mmc.getAvailableConfigGroups()

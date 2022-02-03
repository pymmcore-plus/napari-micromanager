from micromanager_gui.main_window import MainWindow


def test_groups_and_presets(main_window: MainWindow):

    assert main_window.tabWidget.count() == 4
    assert main_window.tabWidget.currentIndex() == 0
    assert main_window.tabWidget.tabText(0) == "Groups and Presets"

    obj_cfg = main_window.objectives_cfg
    assert obj_cfg == "Objective"
    assert list(main_window._mmc.getAvailableConfigs(obj_cfg)) == ["10X", "20X", "40X"]

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

    mm_table = main_window.groups_and_presets.tb
    assert mm_table.native.rowCount() == 5
    assert mm_table.native.columnCount() == 2

    # test channel comboboxes
    _, channel_tab_cbox = mm_table.data[1]  # channel combobox in table
    print("___________ComboBox:", channel_tab_cbox)
    print("___________current text:", channel_tab_cbox.get_value())
    # set channel_tab_cbox to "Rhodamine" -> it should change also snap_channel_comboBox
    channel_tab_cbox.value = "Rhodamine"
    print("___________ComboBox:", channel_tab_cbox)
    print("___________new text:", channel_tab_cbox.get_value())
    print("___________snap cbox text:", main_window.snap_channel_comboBox.currentText())
    assert main_window.snap_channel_comboBox.currentText() == "Rhodamine"
    assert channel_tab_cbox.get_value() == "Rhodamine"

    # set snap_channel_comboBox to "DAPI" -> it should change also channel_tab_cbox
    main_window.snap_channel_comboBox.setCurrentText("DAPI")
    print("#############snap cbox:", main_window.snap_channel_comboBox.currentText())
    print("#############tab cbox:", channel_tab_cbox.get_value())
    assert channel_tab_cbox.get_value() == "DAPI"
    assert main_window.snap_channel_comboBox.currentText() == "DAPI"

    # test objective comboboxes
    _, objective_tab_cbox = mm_table.data[3]
    # set objective_tab_cbox to "20X" -> it should change also objective_comboBox
    objective_tab_cbox.value = "20X"
    assert main_window.objective_comboBox.currentText() == "20X"
    assert objective_tab_cbox.get_value() == "20X"

    # set objective_comboBox to "40X" -> it should change also objective_tab_cbox
    main_window.objective_comboBox.setCurrentText("40X")
    assert objective_tab_cbox.get_value() == "40X"
    assert main_window.objective_comboBox.currentText() == "40X"

    # test camera presets
    _, camera_tab_cbox = mm_table.data[0]
    # set camera_tab_cbox to "MedRes" -> it should change also objective_comboBox
    camera_tab_cbox.value = "MedRes"
    assert main_window.bin_comboBox.currentText() == "2"
    assert camera_tab_cbox.get_value() == "MedRes"

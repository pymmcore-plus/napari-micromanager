from micromanager_gui.main_window import MainWindow


def test_populating_group_preset_table(main_window: MainWindow):

    mmc = main_window._mmc
    table = main_window.group_preset_table_wdg.table_wdg

    assert len(list(mmc.getAvailableConfigGroups())) == 8

    for r in range(table.rowCount()):

        group_name = table.item(r, 0).text()
        wdg = table.cellWidget(r, 1)

        if group_name == "Channel":
            assert set(wdg.allowedValues()) == {"DAPI", "FITC", "Cy5", "Rhodamine"}
            wdg.setValue("FITC")
            assert mmc.getCurrentConfig(group_name) == "FITC"

        elif group_name == "_combobox_no_preset_test":
            assert set(wdg.allowedValues()) == {"1", "2", "4", "8"}
            wdg.setValue("8")
            assert mmc.getProperty("Camera", "Binning") == "8"

        elif group_name == "_lineedit_test":
            assert str(wdg.value()) in {"512", "512.0"}
            wdg.setValue("256")
            assert mmc.getProperty("Camera", "OnCameraCCDXSize") == "256"

        elif group_name == "_slider_test":
            assert type(wdg.value()) == float
            wdg.setValue(0.1)
            assert mmc.getProperty("Camera", "TestProperty1") == "0.1000"

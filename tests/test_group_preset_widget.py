from magicgui.widgets import ComboBox, FloatSlider, LineEdit

from micromanager_gui.main_window import MainWindow


def test_populating_group_preset_table(main_window: MainWindow):

    mmc = main_window._mmc
    table = main_window.group_preset_table_wdg.table_wdg

    assert len(list(mmc.getAvailableConfigGroups())) == 8

    for r in range(table.rowCount()):

        group_name = table.item(r, 0)
        wdg = table.item(r, 1)

        if group_name == "Channel":
            assert type(wdg) == ComboBox
            assert set(wdg.choices) == {"DAPI", "FITC", "Cy5", "Rhodamine"}
            wdg.value = "FITC"
            assert mmc.getCurrentConfig(group_name) == "FITC"

        elif group_name == "_combobox_no_preset_test":
            assert type(wdg) == ComboBox
            assert set(wdg.choices) == {"1", "2", "4", "8"}
            wdg.value = "8"
            assert mmc.getProperty("Camera", "Binning") == "8"

        elif group_name == "_lineedit_test":
            assert type(wdg) == LineEdit
            assert wdg.value == "512"
            wdg.value = "256"
            assert mmc.getProperty("Camera", "OnCameraCCDXSize") == "256"

        elif group_name == "_slider_test":
            assert type(wdg) == FloatSlider
            assert type(wdg.value) == float
            wdg.value = 0.1
            assert mmc.getProperty("Camera", "TestProperty1") == "0.1000"

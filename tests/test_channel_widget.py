from micromanager_gui._gui_objects._channel_widget import ChannelWidget
from micromanager_gui.main_window import MainWindow


def test_channel_widget(
    qtbot,
    main_window: MainWindow,
):

    ch_combo = main_window.tab_wdg.snap_channel_comboBox
    mmc = main_window._mmc
    print(mmc.getAvailableConfigGroups())

    assert mmc.getChannelGroup() == "Channel"

    assert isinstance(ch_combo, ChannelWidget)

    ch_combo.channel_combo.setValue("DAPI")
    assert mmc.getCurrentConfig("Channel") == "DAPI"

    mmc.setConfig("Channel", "FITC")
    assert ch_combo.channel_combo.value() == "FITC"

    # TODO: continue when we have delete group/preset signals

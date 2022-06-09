from micromanager_gui._gui_objects._channel_widget import ChannelWidget
from micromanager_gui.main_window import MainWindow


def test_channel_widget(
    qtbot,
    main_window: MainWindow,
):

    ch_combo = main_window.tab_wdg.snap_channel_comboBox
    mmc = main_window._mmc

    assert mmc.getChannelGroup() == "Channel"

    assert isinstance(ch_combo, ChannelWidget)

    mmc.setProperty("Core", "Shutter", "")
    assert not mmc.getShutterDevice()

    ch_combo.channel_wdg.setValue("DAPI")
    assert mmc.getCurrentConfig("Channel") == "DAPI"
    assert mmc.getShutterDevice() == "Multi Shutter"

    mmc.setConfig("Channel", "FITC")
    assert ch_combo.channel_wdg.value() == "FITC"

    mmc.setProperty("Emission", "Label", "Chroma-HQ700")
    assert ch_combo.channel_wdg._combo.styleSheet() == "color: magenta;"

    mmc.setChannelGroup("")
    assert not ch_combo.channel_wdg.count()

    # TODO: continue when we have delete group/preset signals

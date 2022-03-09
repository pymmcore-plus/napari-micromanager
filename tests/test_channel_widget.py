from pathlib import Path

from qtpy.QtWidgets import QComboBox

from micromanager_gui._core import get_core_singleton
from micromanager_gui._core_widgets._presets_widget import PresetsWidget
from micromanager_gui._gui_objects._channel_widget import ChannelWidget

test_cfg = Path(__file__).parent / "test_config.cfg"


def test_channel_widget(qtbot):

    mmc = get_core_singleton()

    ch_wdg = ChannelWidget()
    qtbot.addWidget(ch_wdg)
    assert isinstance(ch_wdg.channel_combo, QComboBox)

    mmc.loadSystemConfiguration(test_cfg)
    assert isinstance(ch_wdg.channel_combo, PresetsWidget)

    ch_wdg.channel_combo.setValue("DAPI")
    assert mmc.getCurrentConfig("Channel") == "DAPI"

    mmc.setConfig("Channel", "FITC")
    assert ch_wdg.channel_combo.value() == "FITC"

    # TODO: to continue when we have delete group/preset signals

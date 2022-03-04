from pathlib import Path

import pytest

from micromanager_gui._core import get_core_singleton
from micromanager_gui._gui_objects._preset_widget import PresetsWidget

CORE = get_core_singleton()
config_path = Path(__file__).parent.parent / "test_config.cfg"
CORE.loadSystemConfiguration(config_path)

groups = list(CORE.getAvailableConfigGroups())


@pytest.mark.parametrize("group", groups)
def test_preset_widget(group, qtbot):

    presets = list(CORE.getAvailableConfigs(group))

    if len(presets) <= 1:
        return

    wdg = PresetsWidget(group)
    qtbot.addWidget(wdg)
    wdg.show()

    items = [wdg._combo.itemText(i) for i in range(wdg._combo.count())]
    assert items == presets

    CORE.setConfig(group, presets[1])
    assert wdg._combo.currentText() == str(presets[1])

    wdg._combo.setCurrentText(presets[0])
    assert CORE.getCurrentConfig(group) == presets[0]

    wdg._disconnect()

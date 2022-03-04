import pytest

from micromanager_gui._core import get_core_singleton
from micromanager_gui._gui_objects._preset_widget import PresetsWidget

CORE = get_core_singleton()
CORE.loadSystemConfiguration()

groups = list(CORE.getAvailableConfigGroups())


@pytest.mark.parametrize("group", groups)
def test_preset_widget(group, qtbot):

    presets = list(CORE.getAvailableConfigs(group))

    if len(presets) <= 1:
        return

    wdg = PresetsWidget(group)

    items = [wdg._combo.itemText(i) for i in range(wdg._combo.count())]
    assert items == presets

    CORE.setConfig(group, presets[0])
    assert wdg._combo.currentText() == str(presets[0])

    wdg._combo.setCurrentText(presets[1])
    assert CORE.getCurrentConfig(group) == presets[1]

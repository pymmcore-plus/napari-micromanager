from pymmcore_plus import CMMCorePlus

from micromanager_gui._gui_objects._preset_widget import PresetsWidget


def test_preset_widget(qtbot, global_mmcore: CMMCorePlus):

    groups = list(global_mmcore.getAvailableConfigGroups())

    for group in groups:

        presets = list(global_mmcore.getAvailableConfigs(group))

        if len(presets) <= 1:
            return

        wdg = PresetsWidget(group)
        qtbot.addWidget(wdg)
        wdg.show()

        items = [wdg._combo.itemText(i) for i in range(wdg._combo.count())]
        assert items == presets

        global_mmcore.setConfig(group, presets[1])
        assert wdg._combo.currentText() == presets[1]

        wdg._combo.setCurrentText(presets[0])
        assert global_mmcore.getCurrentConfig(group) == presets[0]

        wdg._disconnect()
        # once disconnected, core changes shouldn't call out to the widget
        global_mmcore.setConfig(group, presets[1])
        assert global_mmcore.getCurrentConfig(group) != wdg._combo.currentText()

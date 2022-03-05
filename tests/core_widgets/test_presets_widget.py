from micromanager_gui._core_widgets._presets_widget import PresetsWidget


def test_preset_widget(qtbot, global_mmcore):
    for group in global_mmcore.getAvailableConfigGroups():
        wdg = PresetsWidget(group)
        qtbot.addWidget(wdg)
        presets = list(global_mmcore.getAvailableConfigs(group))
        assert list(wdg.allowedValues()) == presets

        # no need testing the changes of a config group that has <= 1 item
        if len(presets) <= 1:
            return

        with qtbot.waitSignal(global_mmcore.events.configSet):
            global_mmcore.setConfig(group, presets[-1])
        assert wdg.value() == presets[-1] == global_mmcore.getCurrentConfig(group)

        wdg.setValue(presets[0])
        assert global_mmcore.getCurrentConfig(group) == presets[0]

        wdg._disconnect()
        # once disconnected, core changes shouldn't call out to the widget
        global_mmcore.setConfig(group, presets[-1])
        assert global_mmcore.getCurrentConfig(group) != wdg.value()

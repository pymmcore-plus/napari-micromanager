from pymmcore_plus import CMMCorePlus

from micromanager_gui._core_widgets._presets_widget import PresetsWidget


def test_preset_widget(qtbot, global_mmcore: CMMCorePlus):

    groups = list(global_mmcore.getAvailableConfigGroups())

    for group in groups:

        presets = list(global_mmcore.getAvailableConfigs(group))

        if len(presets) <= 1:
            return

        wdg = PresetsWidget(group)
        qtbot.addWidget(wdg)
        wdg.show()

        values = [wdg.itemText(i) for i in range(wdg.count())]
        assert values == presets

        with qtbot.waitSignal(global_mmcore.events.configSet):
            global_mmcore.setConfig(group, presets[1])
        assert wdg.value() == presets[1]

        wdg.setValue(presets[0])
        assert global_mmcore.getCurrentConfig(group) == presets[0]

        wdg._disconnect()
        # once disconnected, core changes shouldn't call out to the widget
        global_mmcore.setConfig(group, presets[1])
        assert global_mmcore.getCurrentConfig(group) != wdg.value()

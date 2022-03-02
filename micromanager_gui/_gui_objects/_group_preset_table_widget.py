from typing import Any

from magicgui.widgets import ComboBox, FloatSlider, LineEdit, Table, Widget
from qtpy import QtWidgets as QtW
from qtpy.QtWidgets import QVBoxLayout

from .. import _core


class MainTable(Table):
    def __init__(self) -> None:
        super().__init__()
        hdr = self.native.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        vh = self.native.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(24)
        self.native.setEditTriggers(QtW.QTableWidget.NoEditTriggers)


class MMGroupPresetTableWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        self._mmc = _core.get_core_singleton()
        self._mmc.events.systemConfigurationLoaded.connect(self._populate_table)

        self.table_wdg = MainTable()
        self.table_wdg.column_headers = ("Groups", "Presets")
        self.table_wdg.show()
        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.table_wdg.native)

    def _on_system_cfg_loaded(self):
        self._populate_table()

    def _populate_table(self):
        self.table_wdg.clear()
        groups = self._mmc.getAvailableConfigGroups()
        if not groups:
            return
        data = []
        for group in groups:
            presets = list(self._mmc.getAvailableConfigs(group))
            wdg = self._set_widget(group, presets)
            data.append([group, wdg])
        self.table_wdg.value = {
            "data": data,
            "index": [],
            "columns": ["Groups", "Presets"],
        }

    def _get_cfg_data(self, group, preset):
        for n, key in enumerate(self._mmc.getConfigData(group, preset)):
            dev = key[0]
            prop = key[1]
            val = key[2]
        return dev, prop, val, (n + 1)

    def _set_float_slider_wdg(self, presets, device, property, value):
        return FloatSlider(
            value=float(value),
            min=float(self._mmc.getPropertyLowerLimit(device, property)),
            max=float(self._mmc.getPropertyUpperLimit(device, property)),
            label=str(property),
            name=f"{presets[0]}",
            annotation=[device, property, value],
        )

    def _set_widget(self, group, presets) -> Widget:
        wdg = None

        device, property, value, count = self._get_cfg_data(group, presets[0])

        if len(presets) > 1:
            wdg = ComboBox(choices=presets, name=f"{presets}", annotation=[])

        else:

            if count == 1 and self._mmc.getAllowedPropertyValues(device, property):
                # if is a combobox without user-defined" presets"
                # but with devices defined presets (e.g. "Binning"->[1,2,4,8])
                prs = self._mmc.getAllowedPropertyValues(device, property)
                wdg = ComboBox(
                    choices=prs, name=f"{presets}", annotation=[device, property]
                )

            elif count == 1 and self._mmc.getPropertyLowerLimit(device, property):
                wdg = self._set_float_slider_wdg(presets, device, property, value)

            elif count > 1:
                wdg = ComboBox(choices=presets, name=f"{presets}", annotation=[])

            else:
                wdg = LineEdit(
                    value=str(value),
                    name=f"{presets[0]}",
                    annotation=[device, property, value],
                )

        @wdg.changed.connect
        def _on_change(value: Any):

            if isinstance(wdg, ComboBox):
                if wdg.annotation:
                    # if is a combobox without user-defined" presets"
                    # but with devices defined presets (e.g. "Binning"->[1,2,4,8])
                    self._mmc.setProperty(device, property, value)  # -> propertyChanged
                else:
                    self._mmc.setConfig(group, value)  # -> configSet
            else:
                if isinstance(wdg, FloatSlider):
                    v = float(value)
                if isinstance(wdg, LineEdit):
                    v = str(value)
                self._mmc.setProperty(device, property, v)  # -> propertyChanged

        return wdg

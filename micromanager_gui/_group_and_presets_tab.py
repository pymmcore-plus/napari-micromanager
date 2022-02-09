from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger
from magicgui.widgets import (
    ComboBox,
    Container,
    FloatSlider,
    LineEdit,
    PushButton,
    Slider,
    Table,
    Widget,
)
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout

from ._util import blockSignals

if TYPE_CHECKING:
    from pymmcore_plus import RemoteMMCore


WDG_TYPE = (FloatSlider, Slider, LineEdit)


class MainTable(Table):
    def __init__(self, mmcore: RemoteMMCore()) -> None:
        super().__init__()
        self.mmcore = mmcore
        hdr = self.native.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        vh = self.native.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(24)
        self.native.setEditTriggers(QtW.QTableWidget.NoEditTriggers)


class GroupPresetWidget(QtW.QWidget):

    table_wdg_changed = Signal(str)
    group_preset_deleted = Signal(str)

    def __init__(self, mmcore: RemoteMMCore, parent=None):
        super().__init__(parent)

        # to disable the logger
        if parent and not parent.log:
            logger.disable(__name__)

        self._mmc = mmcore

        self.dict_table_data = {}

        self.tb = MainTable(self._mmc)
        self.tb.column_headers = ("Groups", "Presets")
        self.tb.show()

        self.new_btn = PushButton(text="New")
        self.edit_btn = PushButton(text="Edit")
        self.rename_btn = PushButton(text="Rename")
        self.delete_gp_btn = PushButton(text="- Group")
        self.delete_gp_btn.clicked.connect(self._delete_selected_group)
        self.delete_ps_btn = PushButton(text="- Preset")
        self.delete_ps_btn.clicked.connect(self._delete_selected_preset)
        self.save_cfg_btn = PushButton(text="Save")

        buttons = Container(
            widgets=[
                self.new_btn,
                self.edit_btn,
                self.rename_btn,
                self.delete_gp_btn,
                self.delete_ps_btn,
                self.save_cfg_btn,
            ],
            labels=False,
            layout="horizontal",
        )

        self.group_presets_widget = Container(
            widgets=[self.tb, buttons],
            labels=True,
            layout="vertical",
        )
        self.group_presets_widget.margins = 0, 0, 0, 0
        self.setLayout(QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.group_presets_widget.native)

    def populate_table(self):
        logger.debug("populate_table")
        groups = self._mmc.getAvailableConfigGroups()
        data = []
        for group in groups:
            presets = self._mmc.getAvailableConfigs(group)
            wdg = self._set_widget(group, presets)
            data.append([group, wdg])
        self.tb.value = {"data": data, "index": [], "columns": ["Groups", "Presets"]}

        self._update_group_table_status()

    def _update_group_table_status(self):

        for row in range(self.tb.shape[0]):

            group, wdg = self.tb.data[row]

            if isinstance(wdg, WDG_TYPE):
                preset = self._mmc.getPropertyFromCache(
                    wdg.annotation[0], wdg.annotation[1]
                )

                if preset:
                    dev, prop = wdg.annotation
                    if isinstance(wdg, Slider):
                        val = int(preset)
                    elif isinstance(wdg, FloatSlider):
                        val = float(preset)
                    elif isinstance(wdg, LineEdit):
                        val = str(preset)

                    with blockSignals(wdg.native):
                        wdg.value = val

            else:
                preset = self._mmc.getCurrentConfigFromCache(group)
                if preset:
                    with blockSignals(wdg.native):
                        wdg.value = preset

    def _get_cfg_data(self, group, preset):
        for n, key in enumerate(self._mmc.getConfigData(group, preset)):
            dev = key[0]
            prop = key[1]
            val = key[2]
        return dev, prop, val, (n + 1)

    def _set_widget(self, group, presets) -> Widget:
        wdg = None

        dev, prop, val, count = self._get_cfg_data(group, presets[0])

        if len(presets) > 1:
            wdg = ComboBox(choices=presets, name=f"{presets}", annotation=[])
        else:
            if count > 1 or self._mmc.getAllowedPropertyValues(dev, prop):
                wdg = ComboBox(choices=presets, name=f"{presets}", annotation=[])
            elif self._mmc.hasPropertyLimits(dev, prop):
                val_type = self._mmc.getPropertyLowerLimit(dev, prop)
                if isinstance(val_type, float):
                    wdg = FloatSlider(
                        value=float(val),
                        min=float(self._mmc.getPropertyLowerLimit(dev, prop)),
                        max=float(self._mmc.getPropertyUpperLimit(dev, prop)),
                        label=str(prop),
                        name=f"{presets}",
                        annotation=[dev, prop],
                    )
                    self._mmc.setProperty(
                        wdg.annotation[0], wdg.annotation[1], wdg.value
                    )
                else:
                    wdg = Slider(
                        value=int(val),
                        min=int(self._mmc.getPropertyLowerLimit(dev, prop)),
                        max=int(self._mmc.getPropertyUpperLimit(dev, prop)),
                        label=str(prop),
                        name=f"{presets}",
                        annotation=[dev, prop],
                    )
                    self._mmc.setProperty(
                        wdg.annotation[0], wdg.annotation[1], wdg.value
                    )
            else:
                wdg = LineEdit(
                    value=str(val), name=f"{presets}", annotation=[dev, prop]
                )
                self._mmc.setProperty(wdg.annotation[0], wdg.annotation[1], wdg.value)

        @wdg.changed.connect
        def _on_change(value: Any):
            if isinstance(wdg, ComboBox):
                self._mmc.setConfig(group, value)  # -> configSet
                self.table_wdg_changed.emit(value)
            else:
                if isinstance(wdg, FloatSlider):
                    v = float(value)
                if isinstance(wdg, LineEdit):
                    v = str(value)
                if isinstance(wdg, Slider):
                    v = int(value)
                self._mmc.setProperty(dev, prop, v)  # -> propertyChanged

        return wdg

    def _delete_selected_group(self):
        selected_rows = {r.row() for r in self.tb.native.selectedIndexes()}
        for row_idx in sorted(selected_rows, reverse=True):
            group = self.tb.data[row_idx, 0]
            self.tb.native.removeRow(row_idx)
            self._mmc.deleteConfigGroup(group)
            logger.debug(f"group {group} deleted!")
            self.group_preset_deleted.emit(group)

    def _delete_selected_preset(self):  # sourcery skip: merge-duplicate-blocks
        selected_rows = {r.row() for r in self.tb.native.selectedIndexes()}
        for row_idx in sorted(selected_rows, reverse=True):
            group = self.tb.data[row_idx, 0]
            wdg = self.tb.data[row_idx, 1]
            if isinstance(wdg, ComboBox):
                if len(wdg.choices) == 1:
                    preset = ""
                    self._mmc.deleteConfigGroup(group)
                    self.tb.native.removeRow(row_idx)
                    logger.debug(f"group {group} deleted!")
                else:
                    preset = str(wdg.value)
                    self._mmc.deleteConfig(group, preset)
                    logger.debug(f"group {group}.{wdg.value} deleted!")
                    wdg.del_choice(wdg.value)
            else:
                preset = ""
                self._mmc.deleteConfigGroup(group)
                self.tb.native.removeRow(row_idx)
                logger.debug(f"group {group} deleted!")

            self.group_preset_deleted.emit(group)

    def _edit_selected_group_preset(self):
        selected_row = [r.row() for r in self.tb.native.selectedIndexes()]

        if not selected_row or len(selected_row) > 1:
            return

        groupname = self.tb.data[selected_row[0], 0]
        wdg = self.tb.data[selected_row[0], 1]

        if isinstance(wdg, ComboBox):
            curr_preset = wdg.value
        else:
            curr_preset = wdg.name.translate({ord(c): None for c in "[]'"})

        item_to_find = self._find_items(groupname, curr_preset)
        item_to_find_list = [x[0] for x in item_to_find]

        return groupname, curr_preset, item_to_find, item_to_find_list

    def _find_items(self, groupname, _to_find):
        return [
            (f"{key[0]}-{key[1]}", key[2])
            for key in self._mmc.getConfigData(groupname, _to_find)
        ]


class RenameGroupPreset(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gp_lineedit = LineEdit()
        self.ps_lineedit = LineEdit()
        self.button = PushButton(text="Rename")

        self.group = Container(
            widgets=[self.gp_lineedit], label="Group:", labels=True, layout="horizontal"
        )
        self.preset = Container(
            widgets=[self.ps_lineedit],
            label="Preset:",
            labels=True,
            layout="horizontal",
        )
        self.main = Container(
            widgets=[self.group, self.preset, self.button],
            labels=True,
            layout="vertical",
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.main.native)

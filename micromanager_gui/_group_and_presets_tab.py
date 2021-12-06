from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from loguru import logger
from magicgui.widgets import (
    ComboBox,
    Container,
    FloatSlider,
    Label,
    LineEdit,
    PushButton,
    Slider,
    Table,
    Widget,
)
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QDialog

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

    update_table = Signal(str)
    on_change_cbox_widget = Signal(str, str)

    def __init__(self, mmcore: RemoteMMCore, parent=None):
        super().__init__(parent)
        self._mmc = mmcore

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

        self._add_to_table()

    def _add_to_table(self):
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
                    wdg.value = val
                    self._mmc.setProperty(dev, prop, val)

            else:
                preset = self._mmc.getCurrentConfigFromCache(group)
                if preset:
                    wdg.value = preset
                    self._mmc.setConfig(group, preset)

        self.update_table.emit("update_table")

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
            wdg = ComboBox(choices=presets, name=f"{presets}", annotation=[dev, prop])
        else:
            if count > 1 or self._mmc.getAllowedPropertyValues(dev, prop):
                wdg = ComboBox(
                    choices=presets, name=f"{presets}", annotation=[dev, prop]
                )
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
                else:
                    wdg = Slider(
                        value=int(val),
                        min=int(self._mmc.getPropertyLowerLimit(dev, prop)),
                        max=int(self._mmc.getPropertyUpperLimit(dev, prop)),
                        label=str(prop),
                        name=f"{presets}",
                        annotation=[dev, prop],
                    )
            else:
                wdg = LineEdit(
                    value=str(val), name=f"{presets}", annotation=[dev, prop]
                )

        @wdg.changed.connect
        def _on_change(value: Any):
            if isinstance(wdg, ComboBox):
                self._mmc.setConfig(group, value)
                self.on_change_cbox_widget.emit(f"{group}", f"{value}")
            else:
                if isinstance(wdg, FloatSlider):
                    v = float(value)
                if isinstance(wdg, LineEdit):
                    v = str(value)
                if isinstance(wdg, Slider):
                    v = int(value)
                self._mmc.setProperty(dev, prop, v)

        return wdg

    def _delete_selected_group(self):
        selected_rows = {r.row() for r in self.tb.native.selectedIndexes()}
        for row_idx in sorted(selected_rows, reverse=True):
            group = self.tb.data[row_idx, 0]
            self.tb.native.removeRow(row_idx)
            self._mmc.deleteConfigGroup(group)
            logger.debug(f"group {group} deleted!")  # logger
            self._update_group_table_status()

    def _delete_selected_preset(self):  # sourcery skip: merge-duplicate-blocks
        selected_rows = {r.row() for r in self.tb.native.selectedIndexes()}
        for row_idx in sorted(selected_rows, reverse=True):
            group = self.tb.data[row_idx, 0]
            wdg = self.tb.data[row_idx, 1]  # [r, c]
            if isinstance(wdg, ComboBox):
                if len(wdg.choices) == 1:
                    self._mmc.deleteConfigGroup(group)
                    self.tb.native.removeRow(row_idx)
                    logger.debug(f"group {group} deleted!")
                else:
                    self._mmc.deleteConfig(group, str(wdg.value))
                    logger.debug(f"group {group}.{wdg.value} deleted!")
                    wdg.del_choice(wdg.value)
            else:
                self._mmc.deleteConfigGroup(group)
                self.tb.native.removeRow(row_idx)
                logger.debug(f"group {group} deleted!")
            self._update_group_table_status()

    def _edit_selected_group_preset(self):
        selected_row = [r.row() for r in self.tb.native.selectedIndexes()]

        if not selected_row or len(selected_row) > 1:
            return

        groupname = self.tb.data[selected_row[0], 0]  # [r, c]
        wdg = self.tb.data[selected_row[0], 1]

        if isinstance(wdg, ComboBox):
            curr_preset = wdg.value
        else:
            curr_preset = wdg.name.translate({ord(c): None for c in "[]'"})
        item_to_find_list = self._create_item_list(groupname, curr_preset)

        return groupname, curr_preset, item_to_find_list

    def _create_item_list(self, groupname, _to_find):
        return [
            f"{key[0]}-{key[1]}" for key in self._mmc.getConfigData(groupname, _to_find)
        ]

    def _open_rename_widget(self):
        if not hasattr(self, "rw"):
            rw = RenameGroupPreset(self._mmc, self.tb, self._add_to_table, self)
        rw.show()


class RenameGroupPreset(QDialog):
    def __init__(
        self, mmcore: RemoteMMCore, table: Table, add_to_table: Callable, parent=None
    ):
        super().__init__(parent)

        self._mmc = mmcore
        self.tb = table
        self.add_to_table = add_to_table

        self.gp_label = Label(label="Group:")
        self.gp_lineedit = LineEdit()
        self.ps_label = Label(label="Preset:")
        self.ps_lineedit = LineEdit()
        self._get_group_and_preset_names()

        self.button = PushButton(text="Rename")
        self.button.clicked.connect(self._rename)

        self.group = Container(
            widgets=[self.gp_label, self.gp_lineedit], labels=True, layout="horizontal"
        )
        self.preset = Container(
            widgets=[self.ps_label, self.ps_lineedit], labels=True, layout="horizontal"
        )
        self.main = Container(
            widgets=[self.group, self.preset, self.button],
            labels=True,
            layout="vertical",
        )

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.main.native)

    def _get_group_and_preset_names(self):
        selected_row = [r.row() for r in self.tb.native.selectedIndexes()]

        if not selected_row or len(selected_row) > 1:
            return

        self.groupname = self.tb.data[selected_row[0], 0]  # [r, c]
        wdg = self.tb.data[selected_row[0], 1]

        if isinstance(wdg, ComboBox):
            self.curr_preset = wdg.value
        else:
            self.curr_preset = wdg.name.translate({ord(c): None for c in "[]'"})

        self.gp_label.value = f"{self.groupname}  ->"
        self.ps_label.value = f"{self.curr_preset}  ->"
        self.gp_lineedit.value = self.groupname
        self.ps_lineedit.value = self.curr_preset

    def _rename(self):
        self._mmc.renameConfigGroup(self.groupname, self.gp_lineedit.value)
        self._mmc.renameConfig(
            self.gp_lineedit.value, self.curr_preset, self.ps_lineedit.value
        )
        logger.debug(
            f"Renamed: {self.groupname}.{self.curr_preset} -> "
            f"{self.gp_lineedit.value}.{self.ps_lineedit.value}"
        )

        self.add_to_table()

        self.close()

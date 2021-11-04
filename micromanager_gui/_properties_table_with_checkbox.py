from dataclasses import dataclass
from typing import Any, Sequence

from magicgui.widgets import (
    CheckBox,
    ComboBox,
    Container,
    FloatSlider,
    LineEdit,
    PushButton,
    Slider,
    Table,
    Widget,
)
from pymmcore_plus import DeviceType, PropertyType
from PyQt5.QtWidgets import QHBoxLayout
from qtpy import QtWidgets
from qtpy.QtWidgets import QDialog

from .prop_browser import iter_dev_props

TABLE_INDEX_LIST = []

OTHER_DEVICES = (
    DeviceType.XYStageDevice,
    DeviceType.SerialDevice,
    DeviceType.GenericDevice,
    DeviceType.AutoFocusDevice,
    DeviceType.CoreDevice,
    DeviceType.ImageProcessorDevice,
    DeviceType.SignalIODevice,
    DeviceType.MagnifierDevice,
    DeviceType.SLMDevice,
    DeviceType.HubDevice,
    DeviceType.GalvoDevice,
)


@dataclass
class PropertyItem:
    device: str
    dev_type: DeviceType
    name: str
    value: Any
    read_only: bool
    pre_init: bool
    has_range: bool
    lower_lim: float
    upper_lim: float
    prop_type: PropertyType
    allowed: Sequence[str]


def get_editor_widget(prop: PropertyItem, mmc) -> Widget:
    if prop.allowed:
        return ComboBox(value=prop.value, choices=prop.allowed)
    elif prop.has_range:
        if PropertyType(prop.prop_type).name == "Float":
            return FloatSlider(
                value=float(prop.value),
                min=float(prop.lower_lim),
                max=float(prop.upper_lim),
                label=f"{prop.device} {prop.name}",
            )
        else:
            return Slider(
                value=int(prop.value),
                min=int(prop.lower_lim),
                max=int(prop.upper_lim),
                label=f"{prop.device} {prop.name}",
            )
    else:
        return LineEdit(value=prop.value)


def create_group_checkboxes(pt: Table, index: int) -> Widget:
    wdg = CheckBox(value=False, annotation=index)

    @wdg.changed.connect
    def _on_toggle():
        if wdg.value:
            TABLE_INDEX_LIST.append(wdg.annotation)
        else:
            idx = TABLE_INDEX_LIST.index(wdg.annotation)
            TABLE_INDEX_LIST.pop(idx)
        print("ROW: ", TABLE_INDEX_LIST)

    return wdg


class PropTable(Table):
    def __init__(self, mmcore) -> None:
        super().__init__()
        self.mmcore = mmcore
        self._update()
        hdr = self.native.horizontalHeader()
        hdr.setSectionResizeMode(hdr.ResizeToContents)
        vh = self.native.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(24)
        self._visible_dtypes = set(DeviceType)
        self._filter_string = ""
        self.native.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

    def _update(self):
        data = []
        row_index = 0
        for p in iter_dev_props(self.mmcore):
            if p.read_only:
                continue
            val = get_editor_widget(p, self.mmcore)
            c_box = create_group_checkboxes(self, row_index)
            data.append([int(p.dev_type), c_box, f"{p.device}-{p.name}", val])
            row_index += 1
        self.value = {
            "data": data,
            "index": [],
            "columns": ["Type", " ", "Property", "Value"],
        }
        self.native.hideColumn(0)

    def _refresh_visibilty(self):
        for i, (dtype, _, prop, _) in enumerate(self.data):
            if dtype in self._visible_dtypes and self.filter_string in prop.lower():
                self.native.showRow(i)
            else:
                self.native.hideRow(i)

    @property
    def filter_string(self):
        return self._filter_string

    @filter_string.setter
    def filter_string(self, val: str):
        self._filter_string = val.lower()
        self._refresh_visibilty()


class GroupConfigurations(QDialog):
    def __init__(self, mmcore=None, parent=None):
        super().__init__(parent)
        self._mmcore = mmcore
        self.pt = PropTable(self._mmcore)
        self.pt.min_width = 550

        self.le = LineEdit(label="Filter:")
        self.le.native.setPlaceholderText("Filter...")
        table = Container(widgets=[self.le, self.pt], labels=False)
        self.pt.show()

        self.group_le = LineEdit(label="Group:")
        self.preset_le = LineEdit(label="Preset")
        group_preset = Container(
            widgets=[self.group_le, self.preset_le], labels=True, layout="horizontal"
        )

        self.create_btn = PushButton(text="Create/Edit")

        # connect
        self.le.changed.connect(self._on_le_change)
        self.create_btn.clicked.connect(self._create_group_and_preset)

        self._container = Container(
            layout="vertical",
            widgets=[table, group_preset, self.create_btn],
            labels=False,
        )
        self._container.margins = 0, 0, 0, 0
        self.setLayout(QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._container.native)

    def _on_le_change(self, value: str):
        self.pt.filter_string = value

    def _create_group_and_preset(self):
        group_name = self.group_le.value
        preset_name = self.preset_le.value

        if not group_name or not preset_name:
            return
        if not TABLE_INDEX_LIST:
            return

        if not self._mmcore.isGroupDefined(group_name):
            self._mmcore.defineConfigGroup(group_name)

        if self._mmcore.isConfigDefined(group_name, preset_name):
            self._mmcore.deleteConfig(group_name, preset_name)

        for r in TABLE_INDEX_LIST:
            ls = self.pt._get_rowi(r)
            _split = ls[2].split("-")
            dev = _split[0]
            prop = _split[1]
            val = ls[3].value

            self._mmcore.defineConfig(group_name, preset_name, dev, prop, str(val))

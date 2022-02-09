from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

from loguru import logger
from magicgui import magicgui
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
from qtpy import QtWidgets
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QDialog, QHBoxLayout

from ._util import blockSignals
from .prop_browser import iter_dev_props

if TYPE_CHECKING:
    from pymmcore_plus import RemoteMMCore


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


def get_editor_widget(prop: PropertyItem) -> Widget:
    if prop.allowed:
        return ComboBox(value=prop.value, choices=prop.allowed)
    elif prop.has_range:
        if PropertyType(prop.prop_type).name == "Float":
            return FloatSlider(
                value=float(prop.value),
                min=float(prop.lower_lim),
                max=float(prop.upper_lim),
                name=f"{prop.device}, {prop.name}",
            )
        else:
            return Slider(
                value=int(prop.value),
                min=int(prop.lower_lim),
                max=int(prop.upper_lim),
                name=f"{prop.device}, {prop.name}",
            )
    else:
        return LineEdit(value=prop.value, name=f"{prop.device}, {prop.name}")


class PropTable(Table):
    def __init__(self, mmcore: "RemoteMMCore") -> None:
        super().__init__()
        self.mmcore = mmcore
        self._update()
        self.native.setColumnWidth(0, 50)
        vh = self.native.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(24)
        self._visible_dtypes = set(DeviceType)
        self._filter_string = ""
        self.native.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

        self.table_index_list = []

    def _update(self):
        data = []
        row_index = 0
        for p in iter_dev_props(self.mmcore):
            if p.read_only:
                continue
            val = get_editor_widget(p)
            c_box = self.create_group_checkboxes(self, row_index)
            data.append([int(p.dev_type), c_box, f"{p.device}-{p.name}", val])
            row_index += 1
        self.value = {
            "data": data,
            "index": [],
            "columns": ["Type", " ", "Property", "Value"],
        }
        self.native.hideColumn(0)

    def set_dtype_visibility(self, dtype: DeviceType, visible: bool):
        _dtype = dtype if isinstance(dtype, (list, tuple)) else (dtype,)
        if visible:
            self._visible_dtypes.update(_dtype)
        else:
            self._visible_dtypes.difference_update(_dtype)
        self._refresh_visibilty()

    def _refresh_visibilty(self):
        for i, (dtype, _, prop, _) in enumerate(self.data):
            if dtype in self._visible_dtypes and self.filter_string in prop.lower():
                self.native.showRow(i)
            else:
                self.native.hideRow(i)

    def _show_only_selected(self, status):
        for i, (_, c_box, _, _) in enumerate(self.data):
            if status:
                if c_box.value:
                    self.native.showRow(i)
                else:
                    self.native.hideRow(i)
            else:
                self._refresh_visibilty()

    def create_group_checkboxes(self, pt: Table, index: int) -> Widget:
        wdg = CheckBox(value=False, annotation=index)

        @wdg.changed.connect
        def _on_toggle():
            if wdg.value:
                self.table_index_list.append(wdg.annotation)
            else:
                idx = self.table_index_list.index(wdg.annotation)
                self.table_index_list.pop(idx)

        return wdg

    @property
    def filter_string(self):
        return self._filter_string

    @filter_string.setter
    def filter_string(self, val: str):
        self._filter_string = val.lower()
        self._refresh_visibilty()


def make_checkboxes(pt):
    c = Container(labels=False)
    dt = [
        ("cameras", DeviceType.CameraDevice),
        ("shutters", DeviceType.ShutterDevice),
        ("stages", DeviceType.StageDevice),
        ("wheels, turrets, etc.", DeviceType.StateDevice),
        ("other devices", OTHER_DEVICES),
    ]
    for label, dtype in dt:

        @magicgui(auto_call=True, dt={"bind": dtype}, vis={"label": label})
        def toggle(vis: bool = True, dt=None):
            pt.set_dtype_visibility(dt, visible=vis)

        toggle.name = label[:2]
        c.append(toggle)

    return c


class GroupConfigurations(QDialog):

    new_group_preset = Signal(str, str)

    def __init__(self, mmcore: "RemoteMMCore", parent=None):
        super().__init__(parent)

        # to disable the logger
        if parent and not parent.log:
            logger.disable(__name__)

        self._mmcore = mmcore
        self.pt = PropTable(self._mmcore)

        self.pt.native.resizeColumnsToContents()

        self.pt.min_width = 550
        self.pt.show()

        self.le = LineEdit(label="Filter:")
        self.le.native.setPlaceholderText("Filter...")
        table = Container(widgets=[self.le, self.pt], labels=False)

        self.cb = make_checkboxes(self.pt)
        self.cb.native.layout().addStretch()
        self.cb.native.layout().setSpacing(0)
        self.cb.show()

        self.cbox_show = CheckBox(text="show only selected")
        self.cbox_show.changed.connect(self.show_hide_selected)

        cbox1 = Container(
            layout="vertical", widgets=[self.cbox_show, self.cb], labels=True
        )

        c_box_tb = Container(layout="horizontal", widgets=[cbox1, table], labels=False)

        self.group_le = LineEdit(label="Group:")
        self.preset_le = LineEdit(label="Preset")
        group_preset = Container(
            widgets=[self.group_le, self.preset_le], labels=True, layout="horizontal"
        )

        self.create_btn = PushButton(text="Create/Edit")
        self.clear_checkboxes_btn = PushButton(text="Clear")

        # connect
        self.le.changed.connect(self._on_le_change)
        self.create_btn.clicked.connect(self._create_group_and_preset)
        self.clear_checkboxes_btn.clicked.connect(self._reset_comboboxes)

        self._container = Container(
            layout="vertical",
            widgets=[
                c_box_tb,
                group_preset,
                self.create_btn,
                self.clear_checkboxes_btn,
            ],
            labels=False,
        )
        self._container.margins = 0, 0, 0, 0
        self.setLayout(QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._container.native)

    def _on_le_change(self, value: str):
        self.pt.filter_string = value

    def show_hide_selected(self, status: bool):
        self.pt._show_only_selected(status)

    def _create_group_and_preset(self):
        group_name = self.group_le.value
        preset_name = self.preset_le.value

        if not group_name or not preset_name:
            return
        if not self.pt.table_index_list:
            return

        if not self._mmcore.isGroupDefined(group_name):
            self._mmcore.defineConfigGroup(group_name)

        if self._mmcore.isConfigDefined(group_name, preset_name):
            self._mmcore.deleteConfig(group_name, preset_name)

        for r in self.pt.table_index_list:
            _, _, dev_prop, wdg = self.pt.data[r]
            _split = dev_prop.split("-")
            dev = _split[0]
            prop = _split[1]
            val = wdg.value

            self._mmcore.defineConfig(group_name, preset_name, dev, prop, str(val))

        logger.debug(f"new group signal sent: {group_name}, {preset_name}")
        self.new_group_preset.emit(group_name, preset_name)

    def _reset_comboboxes(self):
        self.le.value = ""
        self.group_le.value = ""
        self.preset_le.value = ""
        for r in range(self.pt.shape[0]):
            _, checkbox, _, _ = self.pt.data[r]
            if checkbox.value:
                checkbox.value = False

    def _set_checkboxes_status(
        self,
        groupname: str,
        presetname: str,
        item_to_find: list,
        item_to_find_list: list,
    ):

        self.cbox_show.value = False

        self.group_le.value = groupname
        self.preset_le.value = presetname

        if not item_to_find_list:
            return

        matched_item_row = []
        for it in item_to_find_list:
            matching_items = self.pt.native.findItems(it, Qt.MatchContains)
            matched_item_row.append(matching_items[0].row())

        if not matched_item_row:
            return

        for row in matched_item_row:
            checkbox = self.pt.data[row][1]
            checkbox.value = True
            dev_prop = self.pt.data[row][2]
            for item in item_to_find:
                if dev_prop in item:
                    val = item[1]
                    break
            wdg = self.pt.data[row][3]
            with blockSignals(wdg.native):
                wdg.value = val

        self.cbox_show.value = True
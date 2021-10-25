from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator, Sequence

from magicgui import magicgui
from magicgui.widgets import (
    ComboBox,
    Container,
    FloatSlider,
    LineEdit,
    Slider,
    Table,
    Widget,
)
from pymmcore_plus import DeviceType, PropertyType
from PyQt5.QtWidgets import QHBoxLayout
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialog

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus


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


def iter_dev_props(mmc: "CMMCorePlus") -> Iterator[PropertyItem]:
    for dev in mmc.getLoadedDevices():
        dev_type = mmc.getDeviceType(dev)
        for prop in mmc.getDevicePropertyNames(dev):
            yield PropertyItem(
                device=dev,
                name=prop,
                dev_type=dev_type,
                value=mmc.getProperty(dev, prop),
                read_only=mmc.isPropertyReadOnly(dev, prop),
                pre_init=mmc.isPropertyPreInit(dev, prop),
                has_range=mmc.hasPropertyLimits(dev, prop),
                lower_lim=mmc.getPropertyLowerLimit(dev, prop),
                upper_lim=mmc.getPropertyUpperLimit(dev, prop),
                prop_type=mmc.getPropertyType(dev, prop),
                allowed=mmc.getAllowedPropertyValues(dev, prop),
            )


class PropTable(Table):
    def __init__(self, mmcore: "CMMCorePlus") -> None:
        super().__init__()
        self.mmcore = mmcore
        self._update()
        hdr = self.native.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        vh = self.native.verticalHeader()
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(24)
        self._visible_dtypes = set(DeviceType)
        self._filter_string = ""
        self._show_read_only = True

    def _update(self):
        data = []
        for p in iter_dev_props(self.mmcore):
            val = p.value if p.read_only else get_editor_widget(p, self.mmcore)
            data.append([int(p.dev_type), p.read_only, f"{p.device}-{p.name}", val])
        self.value = {
            "data": data,
            "index": [],
            "columns": ["Type", "Read_only", "Property", "Value"],
        }
        self.native.hideColumn(0)
        self.native.hideColumn(1)
        cols = self.shape[1]
        for r, ro in enumerate(self["Read_only"]):
            if ro:
                for c in range(cols):
                    i = self.native.item(r, c)
                    i.setFlags(i.flags() & ~Qt.ItemIsEnabled)

    def set_dtype_visibility(self, dtype: DeviceType, visible: bool):
        _dtype = dtype if isinstance(dtype, (list, tuple)) else (dtype,)
        if visible:
            self._visible_dtypes.update(_dtype)
        else:
            self._visible_dtypes.difference_update(_dtype)
        self._refresh_visibilty()

    def _refresh_visibilty(self):
        for i, (dtype, ro, prop, _) in enumerate(self.data):
            if ro and not self.show_read_only:
                self.native.hideRow(i)
            elif dtype in self._visible_dtypes and self.filter_string in prop.lower():
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

    @property
    def show_read_only(self):
        return self._show_read_only

    @show_read_only.setter
    def show_read_only(self, val: bool):
        self._show_read_only = val
        self._refresh_visibilty()


def get_editor_widget(prop: PropertyItem, mmc) -> Widget:
    wdg = None
    if prop.allowed:
        wdg = ComboBox(value=prop.value, choices=prop.allowed)
    elif prop.has_range:
        if PropertyType(prop.prop_type).name == "Float":
            wdg = FloatSlider(
                value=float(prop.value),
                min=float(prop.lower_lim),
                max=float(prop.upper_lim),
                label=f"{prop.device} {prop.name}",
            )
        else:
            wdg = Slider(
                value=int(prop.value),
                min=int(prop.lower_lim),
                max=int(prop.upper_lim),
                label=f"{prop.device} {prop.name}",
            )
    else:
        wdg = LineEdit(value=prop.value)

    @wdg.changed.connect
    def _on_change(value: Any):
        mmc.setProperty(prop.device, prop.name, value)

    return wdg


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

    @magicgui(auto_call=True, show={"label": "Show read-only"})
    def show_ro(show: bool = True):
        pt.show_read_only = show

    c.append(show_ro)

    return c


class PropBrowser(QDialog):
    def __init__(self, mmcore=None, parent=None):
        super().__init__(parent)
        self.pt = PropTable(mmcore)
        self.le = LineEdit(label="Filter:")
        self.le.native.setPlaceholderText("Filter...")
        self.le.changed.connect(self._on_le_change)
        right = Container(widgets=[self.le, self.pt], labels=False)
        self.cb = make_checkboxes(self.pt)
        self.cb.native.layout().addStretch()
        self.cb.native.layout().setSpacing(0)
        self.pt.show()
        self.cb.show()
        self._container = Container(
            layout="horizontal", widgets=[self.cb, right], labels=False
        )
        self._container.margins = 0, 0, 0, 0
        self.setLayout(QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._container.native)

    def _on_le_change(self, value: str):
        self.pt.filter_string = value


if __name__ == "__main__":
    from pymmcore_plus import CMMCorePlus  # noqa
    from qtpy.QtWidgets import QApplication

    app = QApplication([])

    mmcore = CMMCorePlus()
    mmcore.loadSystemConfiguration("tests/test_config.cfg")
    pb = PropBrowser(mmcore)
    pb.show()
    app.exec()

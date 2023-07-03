from typing import List, Optional, Tuple, cast

from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets import StageWidget
from qtpy.QtCore import QMimeData, Qt
from qtpy.QtGui import QDrag, QDragEnterEvent, QDropEvent, QMouseEvent
from qtpy.QtWidgets import QGroupBox, QHBoxLayout, QSizePolicy, QWidget

STAGE_DEVICES = {DeviceType.Stage, DeviceType.XYStage}


class MMStagesWidget(QWidget):
    """UI elements for stage control widgets."""

    def __init__(
        self, *, parent: Optional[QWidget] = None, mmcore: Optional[CMMCorePlus] = None
    ) -> None:
        super().__init__(parent=parent)

        self.setAcceptDrops(True)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.layout().setSpacing(5)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._mmc = CMMCorePlus.instance()
        self._on_cfg_loaded()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

    def _on_cfg_loaded(self) -> None:
        self._clear()
        sizepolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        stage_dev_list = list(self._mmc.getLoadedDevicesOfType(DeviceType.XYStage))
        stage_dev_list.extend(iter(self._mmc.getLoadedDevicesOfType(DeviceType.Stage)))
        for stage_dev in stage_dev_list:
            if self._mmc.getDeviceType(stage_dev) is DeviceType.XYStage:
                bx = _DragGroupBox("XY Control")
            elif self._mmc.getDeviceType(stage_dev) is DeviceType.Stage:
                bx = _DragGroupBox("Z Control")
            else:
                continue
            bx.setLayout(QHBoxLayout())
            bx.setSizePolicy(sizepolicy)
            bx.layout().addWidget(StageWidget(device=stage_dev))
            self.layout().addWidget(bx)
        self.resize(self.sizeHint())

    def _clear(self) -> None:
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.setParent(QWidget())
                    wdg.deleteLater()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        pos = event.pos()

        wdgs: List[Tuple[int, _DragGroupBox, int, int]] = []
        zones: List[Tuple[int, int]] = []
        for i in range(self.layout().count()):
            wdg = cast(_DragGroupBox, self.layout().itemAt(i).widget())
            wdgs.append((i, wdg, wdg.x(), wdg.x() + wdg.width()))
            zones.append((wdg.x(), wdg.x() + wdg.width()))

        for idx, w, _, _ in wdgs:
            if not w.start_pos:
                continue

            try:
                curr_idx = next(
                    (
                        i
                        for i, z in enumerate(zones)
                        if pos.x() >= z[0] and pos.x() <= z[1]
                    )
                )
            except StopIteration:
                break

            if curr_idx == idx:
                w.start_pos = 0
                break
            cast(QHBoxLayout, self.layout()).insertWidget(curr_idx, w)
            w.start_pos = 0
            break
        event.accept()


class _DragGroupBox(QGroupBox):
    def __init__(self, name: str, start_pos: int = 0) -> None:
        super().__init__()
        self._name = name
        self.start_pos = start_pos

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        drag.setMimeData(mime)
        self.start_pos = event.pos().x()
        drag.exec_(Qt.DropAction.MoveAction)

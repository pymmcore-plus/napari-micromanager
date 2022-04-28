from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from superqt.utils import signals_blocked

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus

from pymmcore import g_Keyword_CoreCamera, g_Keyword_CoreDevice

from micromanager_gui import _core


class ExposureWidget(QtW.QWidget):
    def __init__(
        self,
        camera: str = None,
        *,
        parent: Optional[Qt.QWidget] = None,
        core: Optional[CMMCorePlus] = None,
    ):
        super().__init__()
        self._mmc = core or _core.get_core_singleton()
        self._camera = camera or self._mmc.getCameraDevice()

        self.label = QtW.QLabel()
        self.label.setText(" ms")
        self.label.setMaximumWidth(30)
        self.spinBox = QtW.QDoubleSpinBox()
        self.spinBox.setAlignment(Qt.AlignCenter)
        self.spinBox.setMinimum(1.0)
        self.spinBox.setMaximum(100000.0)
        self.spinBox.setKeyboardTracking(False)
        layout = QtW.QHBoxLayout()
        layout.addWidget(self.spinBox)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self._on_load()
        self._mmc.events.exposureChanged.connect(self._on_exp_changed)
        self._mmc.events.systemConfigurationLoaded.connect(self._on_load)

        self.spinBox.valueChanged.connect(self._mmc.setExposure)

    def setCamera(self, camera: str = None):
        """
        Set which camera this widget tracks

        Parameters
        ----------
        camera : str
            The camera device label. If None then use the current Camera device.
        """
        orig_cam = self._camera
        self._camera = camera or self._mmc.getCameraDevice()
        if orig_cam != self._camera:
            self._on_load()

    def _on_load(self):
        with signals_blocked(self.spinBox):
            if self._camera and self._camera in self._mmc.getLoadedDevices():
                self.setEnabled(True)
                self.spinBox.setValue(self._mmc.getExposure(self._camera))
            else:
                self.setEnabled(False)

    def _on_exp_changed(self, camera: str, exposure: float):
        if camera == self._camera:
            with signals_blocked(self.spinBox):
                self.spinBox.setValue(exposure)

    def _on_exp_set(self, exposure: float):
        self._mmc.setExposure(self._camera, exposure)


class DefaultCameraExposureWidget(ExposureWidget):
    def __init__(
        self, *, parent: Optional[Qt.QWidget] = None, core: Optional[CMMCorePlus] = None
    ):
        super().__init__(core=core)
        self._mmc.events.devicePropertyChanged(
            g_Keyword_CoreDevice, g_Keyword_CoreCamera
        ).connect(self._camera_updated)

    def setCamera(self, camera: str = None, force: bool = False):
        """
        Set which camera this widget tracks. Using this on the
        ``DefaultCameraExposureWidget``widget may cause unexpected
        behavior, instead try to use an ``ExposureWidget``.

        Parameters
        ----------
        camera : str
            The camera device label. If None then use the current Camera device.
        force : bool
            Whether to force a change away from tracking the default camera.
        """
        if not force:
            raise RuntimeError(
                "Setting the camera on a DefaultCameraExposureWidget "
                "may cause it to malfunction. Either use *force=True* "
                " or create an ExposureWidget"
            )
        return super().setCamera(camera)

    def _camera_updated(self, value: str):
        # This will not always fire
        # see https://github.com/micro-manager/mmCoreAndDevices/issues/181
        self._camera = value
        # this will result in a double call of _on_load if this callback
        # was triggered by a configuration load. But I don't see an easy way around that
        # fortunately _on_load should be low cost
        self._on_load()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from pymmcore_plus import CMMCorePlus  # noqa

    CMMCorePlus.instance().loadSystemConfiguration()
    app = QtW.QApplication(sys.argv)
    win = DefaultCameraExposureWidget()
    win.show()
    sys.exit(app.exec_())

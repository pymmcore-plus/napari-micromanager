from Pyro5.api import expose
from qtpy.QtCore import QObject, Signal


class QCoreListener(QObject):
    properties_changed = Signal()
    property_changed = Signal(str, str, object)
    channel_group_changed = Signal(str)
    config_group_changed = Signal(str, str)
    system_configuration_loaded = Signal()
    pixel_size_changed = Signal(float)
    pixel_size_affine_changed = Signal(float, float, float, float, float, float)
    stage_position_changed = Signal(str, float)
    xy_stage_position_changed = Signal(str, float, float)
    exposure_changed = Signal(str, float)
    slm_exposure_changed = Signal(str, float)
    mda_frame_ready = Signal(object, object)

    @expose
    def emit(self, signal_name, args):
        emitter = getattr(self, signal_name, None)
        if emitter:
            emitter.emit(*args)

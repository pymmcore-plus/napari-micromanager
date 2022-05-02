from qtpy.QtCore import QObject, Signal


class ShutterEvents(QObject):
    shutterStateUpdate = Signal(str, bool)  # (shutter_label, bool)

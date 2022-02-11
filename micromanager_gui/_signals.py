from qtpy.QtCore import QObject, Signal

__all__ = [
    "main_window_events",
]


class main_window_events(QObject):
    availableChannelsChanged = Signal(tuple)

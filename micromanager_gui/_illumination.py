import re

from magicgui.widgets import Container
from qtpy.QtWidgets import QDialog, QVBoxLayout

from .prop_browser import get_editor_widget, iter_dev_props

LIGHT_LIST = re.compile("(Intensity|Power|test)s?", re.IGNORECASE)  # for testing


class IlluminationDialog(QDialog):
    def __init__(self, mmcore=None, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self._container = Container(
            widgets=[
                get_editor_widget(prop, mmcore)
                for prop in iter_dev_props(mmcore)
                if LIGHT_LIST.search(prop.name) and prop.has_range
            ],
            labels=True,
        )
        self.layout().addWidget(self._container.native)

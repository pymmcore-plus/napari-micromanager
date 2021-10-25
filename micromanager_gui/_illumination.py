import re

from magicgui.widgets import Container
from qtpy.QtWidgets import QDialog

from .prop_browser import get_editor_widget, iter_dev_props

LIGHT_LIST = re.compile("(Intensity|Power|test)s?", re.IGNORECASE)  # for testing


class Illumination(QDialog):
    def __init__(self, mmcore=None, parent=None):
        super().__init__(parent)

    def make_illumination_gui(mmcore) -> Container:

        return Container(
            widgets=[
                get_editor_widget(prop, mmcore)
                for prop in iter_dev_props(mmcore)
                if LIGHT_LIST.search(prop.name) and prop.has_range
            ],
            labels=True,
        )

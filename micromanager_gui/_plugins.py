from typing import TYPE_CHECKING

from napari_plugin_engine import napari_hook_implementation

if TYPE_CHECKING:
    import napari

from enum import Enum
from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus
from prop_browser import PropBrowser

"""
This module is an example of a barebones function plugin for napari
It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html
"""


@napari_hook_implementation
def napari_experimental_provide_function():
    return [add_lut, hide_show, prop]


def prop():
    mmcore = CMMCorePlus()
    mmcore.loadSystemConfiguration()
    pb = PropBrowser(mmcore)

    return pb.show(run=True)


class Color(Enum):
    gray = "gray"
    green = "green"
    magenta = "magenta"
    yellow = "yellow"
    cyan = "cyan"


def add_lut(viewer: "napari.viewer.Viewer", operation: Color):
    """Add LUT to selected layers."""

    for lay in viewer.layers.selection:
        lay.colormap = operation.value
    return


class HideShow(Enum):
    hide = False
    show = True


def hide_show(viewer: "napari.viewer.Viewer", operation: HideShow):
    """Hide/Show selected layers."""

    for lay in viewer.layers.selection:
        lay.visible = operation.value
    return

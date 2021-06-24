from typing import TYPE_CHECKING

from napari_plugin_engine import napari_hook_implementation

if TYPE_CHECKING:
    import napari

"""
This module is an example of a barebones function plugin for napari
It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html
"""
from typing import TYPE_CHECKING

from enum import Enum
import numpy as np
from napari_plugin_engine import napari_hook_implementation

if TYPE_CHECKING:
    import napari


@napari_hook_implementation
def napari_experimental_provide_function():
    return add_lut

class Color(Enum):
    gray = 'gray'
    green = 'green'
    magenta = 'magenta'
    yellow = 'yellow'
    cyan = 'cyan'

def add_lut(viewer: 'napari.viewer.Viewer', operation: Color):
    """Adds LUT."""

    for l in viewer.layers.selection:
        l.colormap = operation.value
    return



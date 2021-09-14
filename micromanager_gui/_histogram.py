import re

import matplotlib
import napari
import napari.viewer
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
from pymmcore_plus import RemoteMMCore
from qtpy import QtWidgets as QtW


class Histogram:
    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        mmcore: RemoteMMCore,
        histogram_widget: QtW.QWidget,
        parent=None,
    ):

        self._mmc = mmcore
        self.viewer = viewer
        self.histogram_widget = histogram_widget
        super().__init__()

        self.layout_histogram = QtW.QVBoxLayout(self.histogram_widget)
        self.canvas_histogram = FigureCanvas(
            Figure(facecolor="#2B2E37", constrained_layout=True)
        )
        self.ax = self.canvas_histogram.figure.subplots()
        self.ax.set_facecolor("#2B2E37")
        self.ax.tick_params(axis="x", colors="white")
        self.ax.tick_params(axis="y", colors="white")
        self.layout_histogram.addWidget(self.canvas_histogram)

    def histogram(self):

        self.ax.clear()
        max_all_selected_layers = []
        min_all_selected_layers = []

        for layer in self.viewer.layers.selection:
            if isinstance(layer, napari.layers.Image) and layer.visible != 0:

                current_layer_raw = self.viewer.layers[f"{layer}"]
                current_layer_raw_color = current_layer_raw.colormap.name

                if current_layer_raw_color not in matplotlib.colors.CSS4_COLORS:
                    current_layer_raw_color = "gray"

                layer_dims = current_layer_raw.ndim

                try:
                    if layer_dims > 2:
                        dims_idx = self.viewer.dims.current_step
                        current_layer = current_layer_raw.data[dims_idx[:-2]]
                    else:
                        current_layer = current_layer_raw.data

                    bit_depth = self._mmc.getProperty(
                        self._mmc.getCameraDevice(), "PixelType"
                    )
                    bit_depth_number = (re.findall("[0-9]+", bit_depth))[0]

                    bin_range = list(range(2 ** int(bit_depth_number)))
                    self.ax.hist(
                        current_layer.flatten(),
                        bins=bin_range,
                        histtype="step",
                        color=current_layer_raw_color,
                    )

                    min_v_layer = current_layer_raw.contrast_limits[0]
                    max_v_layer = current_layer_raw.contrast_limits[1]

                    min_all_selected_layers.append(min_v_layer)
                    max_all_selected_layers.append(max_v_layer)

                    self.ax.set_xlim(
                        left=np.min(min_all_selected_layers),
                        right=np.max(max_all_selected_layers),
                    )
                except IndexError:
                    pass

        self.canvas_histogram.draw_idle()

from __future__ import annotations

import atexit
import contextlib
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Generator, List, Optional, Tuple

import napari
import numpy as np
import zarr
from napari.experimental import link_layers, unlink_layers
from pymmcore_plus import CMMCorePlus
from pymmcore_plus._util import find_micromanager
from pymmcore_widgets import PixelSizeWidget, PropertyBrowser
from qtpy.QtCore import QPoint, Qt, QTimer
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import create_worker, ensure_main_thread
from useq import MDASequence

from . import _mda_meta
from ._gui_objects._cam_roi_widget import CamROI
from ._gui_objects._group_preset_widget import GroupPreset
from ._gui_objects._hcs_widget import HCSWidgetMain
from ._gui_objects._illumination_widget import IlluminationWidget
from ._gui_objects._mda_widget import MultiDWidget
from ._gui_objects._mm_widget import MicroManagerWidget
from ._gui_objects._sample_explorer_widget import SampleExplorer
from ._gui_objects._stages_widget import MMStagesWidget
from ._mda_meta import SequenceMeta
from ._saving import save_sequence
from ._util import event_indices

if TYPE_CHECKING:
    from typing import Dict

    import napari.layers
    import napari.viewer
    import useq
    from napari._qt.widgets.qt_viewer_dock_widget import QtViewerDockWidget
    from pymmcore_plus.core.events import QCoreSignaler

TOOLBAR_SIZE = 45
TOOL_SIZE = 35
MENU_STYLE = """
    QMenu {
        font-size: 15px;
        border: 1px solid grey;
        border-radius: 3px;
    }
"""


class _MinMax(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        max_min_wdg = QWidget()
        max_min_wdg_layout = QHBoxLayout()
        max_min_wdg_layout.setContentsMargins(0, 0, 0, 0)
        max_min_wdg.setLayout(max_min_wdg_layout)

        self.max_min_val_label_name = QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_val_label_name.setMaximumWidth(70)
        max_min_wdg_layout.addWidget(self.max_min_val_label_name)

        self.max_min_val_label = QLabel()
        max_min_wdg_layout.addWidget(self.max_min_val_label)

        scroll.setWidget(max_min_wdg)
        self.layout().addWidget(scroll)


class MainWindow(MicroManagerWidget):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(self, viewer: napari.viewer.Viewer) -> None:
        super().__init__()

        # create connection to mmcore server or process-local variant
        self._mmc = CMMCorePlus.instance()

        self.viewer = viewer

        adapter_path = find_micromanager()
        if not adapter_path:
            raise RuntimeError(
                "Could not find micromanager adapters. Please run "
                "`python -m pymmcore_plus.install` or install manually and set "
                "MICROMANAGER_PATH."
            )

        self._minmax = _MinMax()
        self.mda = MultiDWidget()
        self.explorer = SampleExplorer()
        self.hcs = HCSWidgetMain()

        self.streaming_timer: QTimer | None = None

        self._mda_meta: SequenceMeta = None  # type: ignore

        # connect mmcore signals
        sig: QCoreSignaler = self._mmc.events

        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        sig.exposureChanged.connect(self._update_live_exp)

        sig.imageSnapped.connect(self.update_viewer)
        sig.imageSnapped.connect(self._stop_live)

        # mda events
        self._mmc.mda.events.frameReady.connect(self._on_mda_frame)
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)
        # self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

        self._mmc.events.startContinuousSequenceAcquisition.connect(self._start_live)
        self._mmc.events.stopSequenceAcquisition.connect(self._stop_live)
        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg_loaded)

        # mapping of str `str(sequence.uid) + channel` -> zarr.Array for each layer
        # being added during an MDA
        self._mda_temp_arrays: Dict[str, zarr.Array] = {}
        # mapping of str `str(sequence.uid) + channel` -> temporary directory where
        # the zarr.Array is stored
        self._mda_temp_files: Dict[str, tempfile.TemporaryDirectory] = {}

        # TODO: consider using weakref here like in pymmc+
        # didn't implement here because this object shouldn't be del'd until
        # napari is closed so probably not a big issue
        # and more importantly because I couldn't get it working with pytest
        # because tempfile seems to register an atexit before we do.
        @atexit.register
        def cleanup() -> None:
            """Clean up temporary files we opened."""
            for v in self._mda_temp_files.values():
                with contextlib.suppress(NotADirectoryError):
                    v.cleanup()

        self.viewer.layers.events.connect(self._update_max_min)
        self.viewer.layers.selection.events.connect(self._update_max_min)
        self.viewer.dims.events.current_step.connect(self._update_max_min)

        self.explorer.metadataInfo.connect(self._on_meta_info)
        self.mda.metadataInfo.connect(self._on_meta_info)
        self.hcs.metadataInfo.connect(self._on_meta_info)

        self.viewer.window.add_dock_widget(self._minmax, name="MinMax", area="left")

        self._add_dock_wdgs()

        # plugins = self._add_plugins_toolbar()
        # self.insertToolBar(self.shutters_toolbar, plugins)

        self.gp_button.clicked.connect(self._show_group_preset)
        self.ill_btn.clicked.connect(self._show_illumination)
        self.stage_btn.clicked.connect(self._show_stages)
        self.prop_browser_btn.clicked.connect(self._show_prop_browser)
        self.px_btn.clicked.connect(self._show_pixel_size_table)
        self.log_btn.clicked.connect(self._show_logger_options)

        self.cam_btn.clicked.connect(self._show_cam_roi)
        # self.viewer.mouse_drag_callbacks.append(self._update_cam_roi_layer)
        # self.tab_wdg.cam_wdg.roiChanged.connect(self._on_roi_info)
        # self.tab_wdg.cam_wdg.crop_btn.clicked.connect(self._on_crop_btn)

        self.mda_button.clicked.connect(self._show_mda)
        self.explorer_button.clicked.connect(self._show_explorer)
        self.hcs_button.clicked.connect(self._show_hcs)

        # connect mouse click event
        self.viewer.mouse_drag_callbacks.append(self._mouse_right_click)

    def _add_dock_wdgs(self) -> None:

        self.viewer.window._qt_window.setTabPosition(
            Qt.RightDockWidgetArea, QTabWidget.North
        )

        self.mda_dock = self._add_mda_dock_wdg()
        self._add_tabbed_dock(self.mda_dock)
        self.mda_dock.hide()

        self.explorer_dock = self._add_explorer_dock_wdg()
        self._add_tabbed_dock(self.explorer_dock)
        self.explorer_dock.hide()

        self.hcs_dock = self._add_hcs_dock_wdg()
        self._add_tabbed_dock(self.hcs_dock)
        self.hcs_dock.hide()

    def _add_mda_dock_wdg(self) -> QtViewerDockWidget:
        return self.viewer.window.add_dock_widget(
            self.mda, name="MDA Widget", area="right", allowed_areas=["left", "right"]
        )

    def _add_explorer_dock_wdg(self) -> QtViewerDockWidget:
        return self.viewer.window.add_dock_widget(
            self.explorer,
            name="Explorer Widget",
            area="right",
            allowed_areas=["left", "right"],
        )

    def _add_hcs_dock_wdg(self) -> QtViewerDockWidget:
        return self.viewer.window.add_dock_widget(
            self.hcs, name="HCS Widget", area="right", allowed_areas=["left", "right"]
        )

    def _add_tabbed_dock(self, dockwidget: QDockWidget) -> None:
        """Add dockwidgets in a tab."""
        widgets = [
            d
            for d in self.viewer.window._qt_window.findChildren(QDockWidget)
            if d.objectName() in {"MDA Widget", "Explorer Widget", "HCS Widget"}
        ]
        if len(widgets) > 1:
            self.viewer.window._qt_window.tabifyDockWidget(widgets[0], dockwidget)

    def _show_group_preset(self) -> None:
        if not hasattr(self, "_group_preset_table_wdg"):
            self._group_preset_table_wdg = GroupPreset(parent=self)
            self._group_preset_table_wdg.setWindowTitle("Groups & Presets")
        self._group_preset_table_wdg.show()
        self._group_preset_table_wdg.raise_()

    def _show_illumination(self) -> None:
        if not hasattr(self, "_illumination"):
            self._illumination = IlluminationWidget(parent=self)
            self._illumination.setWindowTitle("Illumination")
        self._illumination.show()
        self._illumination.raise_()

    def _show_stages(self) -> None:
        if not hasattr(self, "_stages"):
            self._stages = MMStagesWidget(parent=self)
            self._stages.setWindowTitle("Stages Control")
        self._stages.show()
        self._stages.raise_()

    def _show_cam_roi(self) -> None:
        if not hasattr(self, "_cam_roi"):
            self._cam_roi = CamROI(parent=self)
            self._cam_roi.setWindowTitle("Camera ROI")
        self._cam_roi.show()
        self._cam_roi.raise_()

    def _show_prop_browser(self) -> None:
        if not hasattr(self, "_prop_browser"):
            self._prop_browser = PropertyBrowser(self._mmc, self)
            self._prop_browser.setWindowTitle("Property Browser")
        self._prop_browser.show()
        self._prop_browser.raise_()

    def _show_pixel_size_table(self) -> None:
        if not hasattr(self, "_px_size_wdg"):
            self._px_size_wdg = PixelSizeWidget(parent=self)
            self._px_size_wdg.setWindowTitle("Pixel Size")
        self._px_size_wdg.show()

    def _create_debug_logger_widget(self) -> QDialog:
        debug_logger_wdg = QDialog(parent=self)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        debug_logger_wdg.setLayout(layout)
        _checkbox = QCheckBox(text="Debug logger")
        _checkbox.setChecked(False)
        _checkbox.toggled.connect(self._enable_debug_logger)
        layout.addWidget(_checkbox)
        return debug_logger_wdg

    def _enable_debug_logger(self, state: bool) -> None:
        from pymmcore_plus import _logger

        if state:
            _logger.set_log_level("DEBUG")
        else:
            _logger.set_log_level()

    def _show_logger_options(self) -> None:
        if not hasattr(self, "_debug_logger_wdg"):
            self._debug_logger_wdg = self._create_debug_logger_widget()
        self._debug_logger_wdg.show()

    def _show_mda(self) -> None:
        try:
            if self.mda_dock.isHidden():
                self.mda_dock.show()
        except RuntimeError:
            self.mda_dock = self._add_mda_dock_wdg()
            self._add_tabbed_dock(self.mda_dock)
            self.mda_dock.show()
        self.mda_dock.raise_()

    def _show_explorer(self) -> None:
        try:
            if self.explorer_dock.isHidden():
                self.explorer_dock.show()
        except RuntimeError:
            self.explorer_dock = self._add_explorer_dock_wdg()
            self._add_tabbed_dock(self.explorer_dock)
            self.explorer_dock.show()
        self.explorer_dock.raise_()

    def _show_hcs(self) -> None:
        try:
            if self.hcs_dock.isHidden():
                self.hcs_dock.show()
        except RuntimeError:
            self.hcs_dock = self._add_hcs_dock_wdg()
            self._add_tabbed_dock(self.hcs_dock)
            self.hcs_dock.show()
        self.hcs_dock.raise_()

    def _on_sys_cfg_loaded(self) -> None:
        self._enable_tools_buttons(len(self._mmc.getLoadedDevices()) > 1)

    def _on_meta_info(self, meta: SequenceMeta, sequence: MDASequence) -> None:
        self._mda_meta = _mda_meta.SEQUENCE_META.get(sequence, meta)

    def _enable_tools_buttons(self, enabled: bool) -> None:
        self.cam_btn.setEnabled(enabled)
        self.stage_btn.setEnabled(enabled)
        self.ill_btn.setEnabled(enabled)
        self.gp_button.setEnabled(enabled)
        self.prop_browser_btn.setEnabled(enabled)
        self.px_btn.setEnabled(enabled)
        self.log_btn.setEnabled(enabled)

    @ensure_main_thread
    def update_viewer(self, data=None) -> None:
        """Update viewer with the latest image from the camera."""
        if data is None:
            try:
                data = self._mmc.getLastImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return
        try:
            preview_layer = self.viewer.layers["preview"]
            preview_layer.data = data
        except KeyError:
            preview_layer = self.viewer.add_image(data, name="preview")

        preview_layer.metadata["mode"] = "preview"
        preview_layer.metadata["positions"] = [
            (
                [],
                self._mmc.getXPosition() if self._mmc.getXYStageDevice() else None,
                self._mmc.getYPosition() if self._mmc.getXYStageDevice() else None,
                self._mmc.getPosition() if self._mmc.getFocusDevice() else None,
            )
        ]

        self._update_max_min()

        if self.streaming_timer is None:
            self.viewer.reset_view()

    def _update_max_min(self, event: Any = None) -> None:

        min_max_txt = ""
        layers: List[napari.layers.Image] = [
            lr
            for lr in self.viewer.layers.selection
            if isinstance(lr, napari.layers.Image) and lr.visible
        ]

        if not layers:
            self._minmax.max_min_val_label.setText(min_max_txt)
            return

        for layer in layers:
            col = layer.colormap.name
            if col not in QColor.colorNames():
                col = "gray"
            # min and max of current slice
            min_max_show = tuple(layer._calc_data_range(mode="slice"))
            min_max_txt += f'<font color="{col}">{min_max_show}</font>'

        self._minmax.max_min_val_label.setText(min_max_txt)

    def _snap(self) -> None:
        # update in a thread so we don't freeze UI
        create_worker(self._mmc.snap, _start_thread=True)

    def _start_live(self) -> None:
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self.update_viewer)
        self.streaming_timer.start(int(self._mmc.getExposure()))

    def _stop_live(self) -> None:
        if self.streaming_timer:
            self.streaming_timer.stop()
            self.streaming_timer = None

    # def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):

    # oldEngine.events.frameReady.disconnect(self._on_mda_frame)
    # oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
    # oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)

    # newEngine.events.frameReady.connect(self._on_mda_frame)
    # newEngine.events.sequenceStarted.connect(self._on_mda_started)
    # newEngine.events.sequenceFinished.connect(self._on_mda_finished)

    @ensure_main_thread
    def _on_mda_started(self, sequence: useq.MDASequence) -> None:
        """Create temp folder and block gui when mda starts."""
        self._enable_tools_buttons(False)

        if self._mda_meta.mode in ["mda", ""]:
            # work out what the shapes of the mda layers will be
            # depends on whether the user selected Split Channels or not
            shape, channels, labels = self._interpret_split_channels(sequence)
            # create the viewer layers backed by zarr stores
            self._add_mda_channel_layers(tuple(shape), channels, sequence)

        elif self._mda_meta.mode == "explorer":

            if self._mda_meta.translate_explorer:
                shape, positions, labels = self._interpret_explorer_positions(sequence)
                self._add_explorer_positions_layers(tuple(shape), positions, sequence)
            else:
                shape, channels, labels = self._interpret_split_channels(sequence)
                self._add_mda_channel_layers(tuple(shape), channels, sequence)

        elif self._mda_meta.mode == "hcs":
            shape, positions, labels = self._interpret_hcs_positions(sequence)
            self._add_hcs_positions_layers(tuple(shape), positions, sequence)

        # set axis_labels after adding the images to ensure that the dims exist
        self.viewer.dims.axis_labels = labels

    def _get_shape_and_labels(
        self, sequence: MDASequence
    ) -> Tuple[List[str], List[int]]:
        """Determine the shape of layers and the dimension labels."""
        img_shape = self._mmc.getImageHeight(), self._mmc.getImageWidth()
        axis_order = event_indices(next(sequence.iter_events()))
        labels = []
        shape = []
        for i, a in enumerate(axis_order):
            dim = sequence.shape[i]
            labels.append(a)
            shape.append(dim)
        labels.extend(["y", "x"])
        shape.extend(img_shape)

        return labels, shape

    def _get_channel_name_with_index(self, sequence: MDASequence) -> List[str]:
        """Store index in addition to channel.config.

        It is possible to have two or more of the same channel in one sequence.
        """
        channels = []
        for i in sequence.iter_events():
            ch = f"_{i.channel.config}_{i.index['c']:03d}"
            if ch not in channels:
                channels.append(ch)
        return channels

    def _interpret_split_channels(
        self, sequence: MDASequence
    ) -> Tuple[List[int], List[str], List[str]]:
        """
        Determine shape, channels and labels.

        ...based on whether we are splitting on channels
        """
        labels, shape = self._get_shape_and_labels(sequence)
        if self._mda_meta.split_channels:
            channels = self._get_channel_name_with_index(sequence)
            with contextlib.suppress(ValueError):
                c_idx = labels.index("c")
                labels.pop(c_idx)
                shape.pop(c_idx)
        else:
            channels = [""]

        return shape, channels, labels

    def _interpret_explorer_positions(
        self, sequence: MDASequence
    ) -> Tuple[List[int], List[str], List[str]]:
        """Determine shape, positions and labels.

        ...by removing positions index.
        """
        labels, shape = self._get_shape_and_labels(sequence)
        positions = [f"{p.name}_" for p in sequence.stage_positions]
        with contextlib.suppress(ValueError):
            p_idx = labels.index("p")
            labels.pop(p_idx)
            shape.pop(p_idx)

        return shape, positions, labels

    def _interpret_hcs_positions(
        self, sequence: MDASequence
    ) -> Tuple[List[int], List[str], List[str]]:
        """Determine shape, positions and labels.

        ...by removing positions index if not a multi-positions.
        """
        labels, shape = self._get_shape_and_labels(sequence)

        positions = []
        first_pos_name = sequence.stage_positions[0].name.split("_")[0]
        self.multi_pos = 0
        for p in sequence.stage_positions:
            p_name = p.name.split("_")[0]
            if f"{p_name}_" not in positions:
                positions.append(f"{p_name}_")
            elif p.name.split("_")[0] == first_pos_name:
                self.multi_pos += 1

        p_idx = labels.index("p")
        if self.multi_pos == 0:
            shape.pop(p_idx)
            labels.pop(p_idx)
        else:
            shape[p_idx] = self.multi_pos + 1

        return shape, positions, labels

    def _add_mda_channel_layers(
        self, shape: Tuple[int, ...], channels: List[str], sequence: MDASequence
    ) -> None:
        """Create Zarr stores to back MDA and display as new viewer layer(s).

        If splitting on Channels then channels will look like ["BF_000", "GFP_000",...]
        and if we do not split on channels it will look like [""] and only one
        layer/zarr store will be created.
        """
        dtype = f"uint{self._mmc.getImageBitDepth()}"

        # create a zarr store for each channel (or all channels when not splitting)
        # to store the images to display so we don't overflow memory.
        for channel in channels:
            id_ = str(sequence.uid) + channel
            tmp = tempfile.TemporaryDirectory()

            # keep track of temp files so we can clean them up when we quit
            # we can't have them auto clean up because then the zarr wouldn't last
            # till the end
            # TODO: when the layer is deleted we should release the zarr store.
            self._mda_temp_files[id_] = tmp
            self._mda_temp_arrays[id_] = z = zarr.open(
                str(tmp.name), shape=shape, dtype=dtype
            )
            fname = self._mda_meta.file_name if self._mda_meta.should_save else "Exp"
            layer = self.viewer.add_image(z, name=f"{fname}_{id_}", blending="additive")

            # add metadata to layer
            layer.metadata["mode"] = self._mda_meta.mode
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["ch_id"] = f"{channel}"

    def _add_explorer_positions_layers(
        self, shape: Tuple[int, ...], positions: List[str], sequence: MDASequence
    ) -> None:
        """Create Zarr stores to back Explorer and display as new viewer layer(s)."""
        dtype = f"uint{self._mmc.getImageBitDepth()}"

        for pos in positions:
            # TODO: modify id_ to try and divede the grids when saving
            # see also line 378 (layer.metadata["grid"])
            id_ = pos + str(sequence.uid)

            tmp = tempfile.TemporaryDirectory()

            self._mda_temp_files[id_] = tmp
            self._mda_temp_arrays[id_] = z = zarr.open(
                str(tmp.name), shape=shape, dtype=dtype
            )
            fname = self._mda_meta.file_name if self._mda_meta.should_save else "Exp"

            layer = self.viewer.add_image(z, name=f"{fname}_{id_}", blending="additive")

            # add metadata to layer
            # storing event.index in addition to channel.config because it's
            # possible to have two of the same channel in one sequence.
            layer.metadata["mode"] = self._mda_meta.mode
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["grid"] = pos.split("_")[-3]
            layer.metadata["grid_pos"] = pos.split("_")[-2]

    def _get_defaultdict_layers(self, event) -> defaultdict[Any, set]:
        layergroups = defaultdict(set)
        for lay in self.viewer.layers:
            if lay.metadata.get("uid") == event.sequence.uid:
                key = lay.metadata.get("grid")[:8]
                layergroups[key].add(lay)
        return layergroups

    def _add_hcs_positions_layers(
        self, shape: Tuple[int, ...], positions: List[str], sequence: MDASequence
    ) -> None:
        """Create Zarr stores to back HCS and display as new viewer layer(s)."""
        dtype = f"uint{self._mmc.getImageBitDepth()}"

        for pos in positions:
            id_ = pos + str(sequence.uid)
            tmp = tempfile.TemporaryDirectory()

            self._mda_temp_files[id_] = tmp
            self._mda_temp_arrays[id_] = z = zarr.open(
                str(tmp.name), shape=shape, dtype=dtype
            )
            fname = self._mda_meta.file_name if self._mda_meta.should_save else "HCS"

            layer = self.viewer.add_image(z, name=f"{fname}_{id_}")

            layer.metadata["mode"] = self._mda_meta.mode
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["well"] = pos

    @ensure_main_thread
    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        meta = self._mda_meta
        if meta.mode == "mda":
            self._mda_acquisition(image, event, meta)
        elif meta.mode == "explorer":
            if meta.translate_explorer:
                self._explorer_acquisition_translate(image, event, meta)
            else:
                self._explorer_acquisition_stack(image, event)
        elif meta.mode == "hcs":
            self._hcs_acquisition(image, event)

    def _add_stage_pos_metadata(
        self, layer: napari.layers.Image, event: useq.MDAEvent
    ) -> None:
        """Add positions info to layer metadata.

        This info is used in the `_mouse_right_click` method.
        """
        indexes: List[int] = []
        for idx in event.index.items():
            if self._mda_meta.split_channels and idx[0] == "c":
                continue
            if self._mda_meta.translate_explorer and idx[0] == "p":
                continue
            indexes.append(idx[-1])

        try:
            layer.metadata["positions"].append(
                (indexes, event.x_pos, event.y_pos, event.z_pos)
            )
        except KeyError:
            layer.metadata["positions"] = [
                (indexes, event.x_pos, event.y_pos, event.z_pos)
            ]

    def _mda_acquisition(
        self, image: np.ndarray, event: useq.MDAEvent, meta: SequenceMeta
    ) -> None:
        axis_order = list(event_indices(event))
        # Remove 'c' from idxs if we are splitting channels
        # also prepare the channel suffix that we use for keeping track of arrays
        channel = ""
        if meta.split_channels:
            channel = f"_{event.channel.config}_{event.index['c']:03d}"

            # split channels checked but no channels added
            with contextlib.suppress(ValueError):
                axis_order.remove("c")

        # get the actual index of this image into the array and
        # add it to the zarr store
        im_idx = tuple(event.index[k] for k in axis_order)
        self._mda_temp_arrays[str(event.sequence.uid) + channel][im_idx] = image

        # move the viewer step to the most recently added image
        for a, v in enumerate(im_idx):
            self.viewer.dims.set_point(a, v)

        # display
        fname = self._mda_meta.file_name if self._mda_meta.should_save else "Exp"
        layer_name = f"{fname}_{event.sequence.uid}{channel}"
        layer = self.viewer.layers[layer_name]
        layer.visible = False
        layer.visible = True
        layer.reset_contrast_limits()

        # add stage position in metadata
        self._add_stage_pos_metadata(layer, event)

    def _explorer_acquisition_stack(
        self, image: np.ndarray, event: useq.MDAEvent
    ) -> None:
        axis_order = list(event_indices(event))
        im_idx = tuple(event.index[k] for k in axis_order)
        self._mda_temp_arrays[str(event.sequence.uid)][im_idx] = image

        for a, v in enumerate(im_idx):
            self.viewer.dims.set_point(a, v)

        fname = self._mda_meta.file_name if self._mda_meta.should_save else "Exp"
        layer = self.viewer.layers[f"{fname}_{event.sequence.uid}"]
        layer.visible = False
        layer.visible = True
        layer.reset_contrast_limits()

        self._add_stage_pos_metadata(layer, event)

    def _explorer_acquisition_translate(
        self, image: np.ndarray, event: useq.MDAEvent, meta: SequenceMeta
    ) -> None:
        axis_order = list(event_indices(event))

        with contextlib.suppress(ValueError):
            axis_order.remove("p")

        im_idx = tuple(event.index[k] for k in axis_order)
        pos_name = event.pos_name
        layer_name = f"{pos_name}_{event.sequence.uid}"
        self._mda_temp_arrays[layer_name][im_idx] = image

        x = meta.explorer_translation_points[event.index["p"]][0]
        y = -meta.explorer_translation_points[event.index["p"]][1]

        layergroups = self._get_defaultdict_layers(event)
        # unlink layers to translate
        for group in layergroups.values():
            unlink_layers(group)

        # translate only once
        fname = self._mda_meta.file_name if self._mda_meta.should_save else "Exp"
        layer = self.viewer.layers[f"{fname}_{layer_name}"]
        if (layer.translate[-2], layer.translate[-1]) != (y, x):
            layer.translate = (y, x)
        layer.metadata["translate"] = True

        self._add_stage_pos_metadata(layer, event)

        # link layers after translation
        for group in layergroups.values():
            link_layers(group)

        for a, v in enumerate(im_idx):
            self.viewer.dims.set_point(a, v)

        layer.visible = False
        layer.visible = True
        layer.reset_contrast_limits()

        zoom_out_factor = (
            self.explorer.scan_size_r
            if self.explorer.scan_size_r >= self.explorer.scan_size_c
            else self.explorer.scan_size_c
        )
        self.viewer.camera.zoom = 1 / zoom_out_factor
        self.viewer.reset_view()

    def _hcs_acquisition(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        axis_order = list(event_indices(event))
        if self.multi_pos == 0:
            axis_order.remove("p")

        # get the actual index of this image into the array
        # add it to the zarr store
        im_idx: Tuple[int, ...] = ()
        for k in axis_order:
            if k == "p" and self.multi_pos > 0:
                im_idx = im_idx + (int(event.pos_name[-3:]),)
            else:
                im_idx = im_idx + (event.index[k],)

        pos_name = event.pos_name.split("_")[0]
        layer_name = f"{pos_name}_{event.sequence.uid}"
        self._mda_temp_arrays[layer_name][im_idx] = image

        # translate only once
        fname = self._mda_meta.file_name if self._mda_meta.should_save else "HCS"
        layer = self.viewer.layers[f"{fname}_{layer_name}"]

        # move the viewer step to the most recently added image
        for a, v in enumerate(im_idx):
            self.viewer.dims.set_point(a, v)

        layer.visible = False
        layer.visible = True
        layer.reset_contrast_limits()

        # add stage position in metadata
        self._add_stage_pos_metadata(layer, event)

        self.viewer.reset_view()

    def _on_mda_finished(self, sequence: useq.MDASequence) -> None:
        """Save layer and add increment to save name."""
        meta = self._mda_meta
        meta = _mda_meta.SEQUENCE_META.pop(sequence, self._mda_meta)
        save_sequence(sequence, self.viewer.layers, meta)
        # reactivate gui when mda finishes.
        self._enable_tools_buttons(True)

    def _update_live_exp(self, camera: str, exposure: float) -> None:
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

    def _mouse_right_click(
        self, viewer: napari.viewer.Viewer, event: Any
    ) -> Generator[None, None, None]:

        if not self._mmc.getXYStageDevice() and not self._mmc.getFocusDevice():
            return

        if self._mmc.getPixelSizeUm() == 0:
            return

        dragged = False
        yield
        # on move
        while event.type == "mouse_move":
            dragged = True
            yield
        if dragged:
            return
        # only right click
        if event.button != 2:
            return

        layer, viewer_coords = self._get_active_layer_and_click_coords(viewer)

        # don't open the menu if the click is not on the layer
        if layer is None or viewer_coords is None:
            return

        x, y, z = self._get_xyz_positions(layer)

        if x is None and y is None and z is None:
            return

        if x is None or y is None:
            new_pos = (x, y, z)
        else:
            new_pos = self._calculate_clicked_stage_coordinates(
                layer, viewer_coords, x, y, z
            )

        r_menu = self._create_right_click_menu(new_pos)
        r_menuPosition = self.viewer.window._qt_viewer.mapToGlobal(
            QPoint(event.pos[0], event.pos[1])
        )
        r_menu.move(r_menuPosition)
        r_menu.show()

    def _get_active_layer_and_click_coords(
        self, viewer: napari.viewer.Viewer
    ) -> Tuple[napari.layers.Image | None, Tuple[int, int]] | Tuple[None, None]:

        # only Image layers
        layers: List[napari.layers.Image] = [
            lr
            for lr in viewer.layers.selection
            if isinstance(lr, napari.layers.Image) and lr.visible
        ]

        if not layers:
            return None, None

        # if not explorer, select only top later
        if layers[-1].metadata["mode"] != "explorer":
            layers = [layers[-1]]
        # if top selected layer is from an explorer experiment
        # make sure all and only linked layers are selected
        # note: the napari 'layer_is_linked' method is not yet public
        # so here we used the 'uid'
        else:
            _id = layers[-1].metadata["uid"]
            layers.clear()
            layers = [ly for ly in viewer.layers if ly.metadata.get("uid") == _id]

        viewer_coords = (
            round(viewer.cursor.position[-2]),
            round(viewer.cursor.position[-1]),
        )

        # get which layer has been clicked depending on the px value.
        # only the clicked layer has a val=value, in the other val=None
        vals = []
        layer: napari.layers.Image | None = None
        for lyr in layers:
            data_coordinates = lyr.world_to_data(viewer_coords)
            val = lyr.get_value(data_coordinates)
            vals.append(val)
            if val is not None:
                layer = lyr

        if vals.count(None) == len(layers):
            layer = None

        return layer, viewer_coords

    def _get_xyz_positions(
        self, layer: napari.layers.Image
    ) -> Tuple[float | None, float | None, float | None]:

        info: List[
            Tuple[List[int], float | None, float | None, float | None]
        ] = layer.metadata.get("positions")

        current_dispalyed_dim = list(self.viewer.dims.current_step[:-2])

        pos: Tuple[float | None, float | None, float | None] = (None, None, None)
        for i in info:
            indexes, x, y, z = i
            # if a MDA layer is in the viewer, by default len(indexes) is minimum 2
            # if there are single channel explorer layers, len(indexes) is 1 and
            # 'pos' variable will be (None, None, None). To avoid that, we set the
            # indexes as an empty list (as for 'preview')
            if layer.metadata.get("mode") == "explorer" and len(indexes) == 1:
                indexes = []
            if indexes == current_dispalyed_dim or not indexes:
                pos = (x, y, z)
                break
        return pos

    def _calculate_clicked_stage_coordinates(
        self,
        layer: napari.layers.Image,
        viewer_coords: Tuple[int, int],
        x: float | None,
        y: float | None,
        z: float | None,
    ) -> Tuple[float, float, float | None]:

        width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
        height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

        # get clicked px stage coords
        top_left = layer.data_to_world((0, 0))[-2:]
        central_px = (top_left[0] + (height // 2), top_left[1] + (width // 2))

        # top left corner of image in um
        x0 = float(x - (central_px[1] * self._mmc.getPixelSizeUm()))
        y0 = float(y + (central_px[0] * self._mmc.getPixelSizeUm()))

        stage_x = x0 + (viewer_coords[1] * self._mmc.getPixelSizeUm())
        stage_y = y0 - (viewer_coords[0] * self._mmc.getPixelSizeUm())

        return stage_x, stage_y, z

    def _create_right_click_menu(
        self, xyz_positions: Tuple[float | None, float | None, float | None]
    ) -> QMenu:

        coord_x, coord_y, coord_z = xyz_positions

        dlg_menu = QMenu(parent=self)
        dlg_menu.setStyleSheet(MENU_STYLE)

        if self._mmc.getXYStageDevice() and coord_x is not None and coord_y is not None:
            xy = dlg_menu.addAction(f"Move to [x:{coord_x},  y:{coord_y}].")
            xy.triggered.connect(lambda: self._move_to_xy(xyz_positions))

        if self._mmc.getFocusDevice() and coord_z is not None:
            z = dlg_menu.addAction(f"Move to [z:{coord_z}].")
            z.triggered.connect(lambda: self._move_to_z(xyz_positions))

        if self._mmc.getXYStageDevice() and self._mmc.getFocusDevice():
            xyz = dlg_menu.addAction(
                f"Move to [x:{coord_x},  y:{coord_y},  z:{coord_z}]."
            )
            xyz.triggered.connect(lambda: self._move_to_xyz(xyz_positions))

        to_mda = dlg_menu.addAction("Add to MDA position table.")
        to_mda.triggered.connect(lambda: self._add_to_mda_position_table(xyz_positions))

        to_explorer = dlg_menu.addAction("Add to Explorer position table.")
        to_explorer.triggered.connect(
            lambda: self._add_to_explorer_position_table(xyz_positions)
        )

        return dlg_menu

    def _move_to_xy(
        self, xyz_positions: Tuple[float | None, float | None, float | None]
    ) -> None:
        x, y, _ = xyz_positions
        if x is None or y is None:
            return
        self._mmc.setXYPosition(x, y)

    def _move_to_z(
        self, xyz_positions: Tuple[float | None, float | None, float | None]
    ) -> None:
        _, _, z = xyz_positions
        if z is None:
            return
        self._mmc.setPosition(z)

    def _move_to_xyz(
        self, xyz_positions: Tuple[float | None, float | None, float | None]
    ) -> None:
        x, y, z = xyz_positions
        if x is None or y is None or z is None:
            return
        self._mmc.setXYPosition(x, y)
        self._mmc.setPosition(z)

    def _add_to_mda_position_table(
        self, xyz_positions: Tuple[float | None, float | None, float | None]
    ) -> None:
        x, y, z = xyz_positions

        idx = self.mda._add_position_row()

        name = QTableWidgetItem("Pos000")
        name.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.mda.stage_tableWidget.setItem(idx, 0, name)

        xpos = QTableWidgetItem(str(x))
        xpos.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.mda.stage_tableWidget.setItem(idx, 1, xpos)

        ypos = QTableWidgetItem(str(y))
        ypos.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.mda.stage_tableWidget.setItem(idx, 2, ypos)

        zpos = QTableWidgetItem(str(z) if z is not None else "")
        zpos.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.mda.stage_tableWidget.setItem(idx, 3, zpos)

        self.mda._rename_positions(["Pos"])

    def _add_to_explorer_position_table(
        self, xyz_positions: Tuple[float | None, float | None, float | None]
    ) -> None:
        x, y, z = xyz_positions

        idx = self.explorer._add_position_row()

        name = QTableWidgetItem("Grid_000")
        name.setWhatsThis("Grid_000")
        name.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.explorer.stage_tableWidget.setItem(idx, 0, name)

        xpos = QTableWidgetItem(str(x))
        xpos.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.explorer.stage_tableWidget.setItem(idx, 1, xpos)

        ypos = QTableWidgetItem(str(y))
        ypos.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.explorer.stage_tableWidget.setItem(idx, 2, ypos)

        zpos = QTableWidgetItem(str(z) if z is not None else "")
        zpos.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.explorer.stage_tableWidget.setItem(idx, 3, zpos)

        self.explorer._rename_positions()

    # def _get_roi_layer(self) -> napari.layers.shapes.shapes.Shapes:
    #     for layer in self.viewer.layers:
    #         if layer.metadata.get("layer_id"):
    #             return layer

    # def _on_roi_info(
    #     self, start_x: int, start_y: int, width: int, height: int, mode: str = ""
    # ) -> None:

    #     layers = {layer.name for layer in self.viewer.layers}
    #     if "preview" not in layers:
    #         self._mmc.snap()

    #     if mode == "Full":
    #         self._on_crop_btn()
    #         return

    #     try:
    #         cam_roi_layer = self._get_roi_layer()
    #         cam_roi_layer.data = self._set_cam_roi_shape(
    #             start_x, start_y, width, height
    #         )
    #     except AttributeError:
    #         cam_roi_layer = self.viewer.add_shapes(name="set_cam_ROI")
    #         cam_roi_layer.metadata["layer_id"] = "set_cam_ROI"
    #         cam_roi_layer.data = self._set_cam_roi_shape(
    #             start_x, start_y, width, height
    #         )

    #     cam_roi_layer.mode = "select"
    #     self.viewer.reset_view()

    # def _set_cam_roi_shape(
    #     self, start_x: int, start_y: int, width: int, height: int
    # ) -> List[list]:
    #     return [
    #         [start_y, start_x],
    #         [start_y, width + start_x],
    #         [height + start_y, width + start_x],
    #         [height + start_y, start_x],
    #     ]

    # def _on_crop_btn(self):
    #     with contextlib.suppress(Exception):
    #         cam_roi_layer = self._get_roi_layer()
    #         self.viewer.layers.remove(cam_roi_layer)
    #     self.viewer.reset_view()

    # def _update_cam_roi_layer(self, layer, event) -> None:  # type: ignore

    #     active_layer = self.viewer.layers.selection.active
    #     if not isinstance(active_layer, napari.layers.shapes.shapes.Shapes):
    #         return

    #     if active_layer.metadata.get("layer_id") != "set_cam_ROI":
    #         return

    #     # on mouse pressed
    #     dragged = False
    #     yield
    #     # on mouse move
    #     while event.type == "mouse_move":
    #         dragged = True
    #         yield
    #     # on mouse release
    #     if dragged:
    #         if not active_layer.data:
    #             return
    #         data = active_layer.data[-1]

    #         x_max = self.tab_wdg.cam_wdg.chip_size_x
    #         y_max = self.tab_wdg.cam_wdg.chip_size_y

    #         x = round(data[0][1])
    #         y = round(data[0][0])
    #         width = round(data[1][1] - x)
    #         height = round(data[2][0] - y)

    #         # change shape if out of cam area
    #         if x + width >= x_max:
    #             x = x - ((x + width) - x_max)
    #         if y + height >= y_max:
    #             y = y - ((y + height) - y_max)

    #         cam = self._mmc.getCameraDevice()
    #         self._mmc.events.roiSet.emit(cam, x, y, width, height)

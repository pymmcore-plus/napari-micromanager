from __future__ import annotations

import atexit
import contextlib
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, List, Tuple

import napari
import numpy as np
import zarr
from napari.experimental import link_layers, unlink_layers
from pymmcore_plus import CMMCorePlus
from pymmcore_plus._util import find_micromanager
from pymmcore_widgets import PixelSizeWidget, PropertyBrowser
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QTimer
from qtpy.QtGui import QColor
from superqt.utils import create_worker, ensure_main_thread
from useq import MDASequence

from . import _mda_meta

# from ._camera_roi import _CameraROI
from ._gui_objects._mm_widget import MicroManagerWidget
from ._mda_meta import SequenceMeta
from ._saving import save_sequence
from ._util import event_indices

if TYPE_CHECKING:
    from typing import Dict

    import napari.layers
    import napari.viewer
    import useq
    from pymmcore_plus.core.events import QCoreSignaler
    from pymmcore_plus.mda import PMDAEngine


class MainWindow(MicroManagerWidget):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(self, viewer: napari.viewer.Viewer, remote=False):
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

        # add mda and explorer tabs to mm_tab widget
        sizepolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding
        )
        self.tab_wdg.setSizePolicy(sizepolicy)

        self.streaming_timer: QTimer | None = None

        self._mda_meta: SequenceMeta = None  # type: ignore

        # disable gui
        self._set_enabled(False)

        # connect mmcore signals
        sig: QCoreSignaler = self._mmc.events

        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        sig.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        sig.exposureChanged.connect(self._update_live_exp)

        sig.imageSnapped.connect(self.update_viewer)
        sig.imageSnapped.connect(self._stop_live)

        # mda events
        self._mmc.mda.events.frameReady.connect(self._on_mda_frame)
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)
        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

        self._mmc.events.startContinuousSequenceAcquisition.connect(self._start_live)
        self._mmc.events.stopSequenceAcquisition.connect(self._stop_live)

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
        def cleanup():
            """Clean up temporary files we opened."""
            for v in self._mda_temp_files.values():
                with contextlib.suppress(NotADirectoryError):
                    v.cleanup()

        self.viewer.layers.events.connect(self._update_max_min)
        self.viewer.layers.selection.events.active.connect(self._update_max_min)
        self.viewer.dims.events.current_step.connect(self._update_max_min)
        # self.viewer.mouse_drag_callbacks.append(self._get_event_explorer)

        self.explorer.metadataInfo.connect(self._on_meta_info)
        self.mda.metadataInfo.connect(self._on_meta_info)
        self.hcs.metadataInfo.connect(self._on_meta_info)
        self.viewer.mouse_drag_callbacks.append(self._update_cam_roi_layer)
        self.tab_wdg.cam_wdg.roiInfo.connect(self._on_roi_info)
        self.tab_wdg.cam_wdg.crop_btn.clicked.connect(self._on_crop_btn)

        self._add_menu()

    def _on_meta_info(self, meta: SequenceMeta, sequence: MDASequence) -> None:
        self._mda_meta = _mda_meta.SEQUENCE_META.get(sequence, meta)

    def _add_menu(self):
        w = getattr(self.viewer, "__wrapped__", self.viewer).window  # don't do this.
        self._menu = QtW.QMenu("&Micro-Manager", w._qt_window)

        action = self._menu.addAction("Device Property Browser...")
        action.triggered.connect(self._show_prop_browser)

        action_1 = self._menu.addAction("Set Pixel Size...")
        action_1.triggered.connect(self._show_pixel_size_table)

        bar = w._qt_window.menuBar()
        bar.insertMenu(list(bar.actions())[-1], self._menu)

    def _show_prop_browser(self):
        if not hasattr(self, "_prop_browser"):
            self._prop_browser = PropertyBrowser(self._mmc, self)
        self._prop_browser.show()
        self._prop_browser.raise_()

    def _show_pixel_size_table(self):
        if not hasattr(self, "_px_size_wdg"):
            self._px_size_wdg = PixelSizeWidget(parent=self)
        self._px_size_wdg.show()

    def _on_system_cfg_loaded(self):
        if len(self._mmc.getLoadedDevices()) > 1:
            self._set_enabled(True)

    def _set_enabled(self, enabled):
        if self._mmc.getCameraDevice():
            # self._camera_group_wdg(enabled)
            self.tab_wdg.snap_live_tab.setEnabled(enabled)
            self.tab_wdg.snap_live_tab.setEnabled(enabled)
        else:
            # self._camera_group_wdg(False)
            self.tab_wdg.snap_live_tab.setEnabled(False)
            self.tab_wdg.snap_live_tab.setEnabled(False)

        # self.illum_btn.setEnabled(enabled)
        # self.ill.setEnabled(enabled)

        self.mda._set_enabled(enabled)
        self.mda.save_groupBox.setEnabled(enabled)

        if self._mmc.getXYStageDevice():
            self.explorer._set_enabled(enabled)
        else:
            self.explorer._set_enabled(False)

        self.explorer.save_explorer_groupBox.setEnabled(enabled)

    # def _camera_group_wdg(self, enabled):
    #     self.cam_wdg.setEnabled(enabled)

    @ensure_main_thread
    def update_viewer(self, data=None):
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

        self._update_max_min()

        if self.streaming_timer is None:
            self.viewer.reset_view()

    def _update_max_min(self, event=None):

        if self.tab_wdg.tabWidget.currentIndex() != 0:
            return

        min_max_txt = ""

        for layer in self.viewer.layers.selection:

            if isinstance(layer, napari.layers.Image) and layer.visible:

                col = layer.colormap.name

                if col not in QColor.colorNames():
                    col = "gray"

                # min and max of current slice
                min_max_show = tuple(layer._calc_data_range(mode="slice"))
                min_max_txt += f'<font color="{col}">{min_max_show}</font>'

        self.tab_wdg.max_min_val_label.setText(min_max_txt)

    def _snap(self):
        # update in a thread so we don't freeze UI
        create_worker(self._mmc.snap, _start_thread=True)

    def _start_live(self):
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self.update_viewer)
        self.streaming_timer.start(int(self._mmc.getExposure()))

    def _stop_live(self):
        if self.streaming_timer:
            self.streaming_timer.stop()
            self.streaming_timer = None

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):
        oldEngine.events.frameReady.disconnect(self._on_mda_frame)
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)

        newEngine.events.frameReady.connect(self._on_mda_frame)
        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)

    @ensure_main_thread
    def _on_mda_started(self, sequence: useq.MDASequence):
        """Create temp folder and block gui when mda starts."""
        self._set_enabled(False)

        if self._mda_meta.mode == "":
            # originated from user script - assume it's an mda
            self._mda_meta.mode = "mda"

        if self._mda_meta.mode == "mda":
            # work out what the shapes of the layers will be
            # this depends on whether the user selected Split Channels or not
            shape, channels, labels = self._interpret_split_channels(sequence)

            # acutally create the viewer layers backed by zarr stores
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

    def _get_shape_and_labels(self, sequence: MDASequence):
        """Determine the shape of layers and the dimension labels."""
        img_shape = self._mmc.getImageHeight(), self._mmc.getImageWidth()
        # dimensions labels
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

    def _interpret_split_channels(
        self, sequence: MDASequence
    ) -> Tuple[List[int], List[str], List[str]]:
        """
        Determine channels based on whether we are splitting on channels.

        ...based on whether we are splitting on channel
        """
        labels, shape = self._get_shape_and_labels(sequence)
        if self._mda_meta.split_channels:
            channels = [f"_{c.config}" for c in sequence.channels]
            with contextlib.suppress(ValueError):
                c_idx = labels.index("c")
                labels.pop(c_idx)
                shape.pop(c_idx)
        else:
            channels = [""]

        return shape, channels, labels

    def _add_mda_channel_layers(
        self, shape: Tuple[int, ...], channels: List[str], sequence: MDASequence
    ):
        """Create Zarr stores to back MDA and display as new viewer layer(s).

        If splitting on Channels then channels will look like ["BF", "GFP",...]
        and if we do not split on channels it will look like [""] and only one
        layer/zarr store will be created.
        """
        dtype = f"uint{self._mmc.getImageBitDepth()}"

        # create a zarr store for each channel (or all channels when not splitting)
        # to store the images to display so we don't overflow memory.
        for i, channel in enumerate(channels):
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
            # storing event.index in addition to channel.config because it's
            # possible to have two of the same channel in one sequence.
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["ch_id"] = f"{channel}_idx{i}"

    def _interpret_explorer_positions(
        self, sequence: MDASequence
    ) -> Tuple[List[int], List[str], List[str]]:
        """Remove positions index and set layer names."""
        labels, shape = self._get_shape_and_labels(sequence)
        positions = [f"{p.name}_" for p in sequence.stage_positions]
        with contextlib.suppress(ValueError):
            p_idx = labels.index("p")
            labels.pop(p_idx)
            shape.pop(p_idx)

        return shape, positions, labels

    def _add_explorer_positions_layers(
        self, shape: Tuple[int, ...], positions: List[str], sequence: MDASequence
    ):
        dtype = f"uint{self._mmc.getImageBitDepth()}"

        # create a zarr store for each channel (or all channels when not splitting)
        # to store the images to display so we don't overflow memory.
        for pos in positions:
            # TODO: modify id_ to try and divede the grids when saving
            # see also line 378 (layer.metadata["grid"])
            id_ = pos + str(sequence.uid)

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
            # storing event.index in addition to channel.config because it's
            # possible to have two of the same channel in one sequence.
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["grid"] = pos.split("_")[-3]
            layer.metadata["grid_pos"] = pos.split("_")[-2]

    def _get_defaultdict_layers(self, event):
        layergroups = defaultdict(set)
        for lay in self.viewer.layers:
            if lay.metadata.get("uid") == event.sequence.uid:
                key = lay.metadata.get("grid")[:8]
                layergroups[key].add(lay)
        return layergroups

    def _interpret_hcs_positions(
        self, sequence: MDASequence
    ) -> Tuple[List[int], List[str], List[str]]:
        """Get positions, labels and shape for the zarr array."""
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

    def _add_hcs_positions_layers(
        self, shape: Tuple[int, ...], positions: List[str], sequence: MDASequence
    ):
        dtype = f"uint{self._mmc.getImageBitDepth()}"

        # create a zarr store for each channel (or all channels when not splitting)
        # to store the images to display so we don't overflow memory.
        for pos in positions:

            id_ = pos + str(sequence.uid)

            tmp = tempfile.TemporaryDirectory()

            # keep track of temp files so we can clean them up when we quit
            # we can't have them auto clean up because then the zarr wouldn't last
            # till the end
            # TODO: when the layer is deleted we should release the zarr store.
            self._mda_temp_files[id_] = tmp
            self._mda_temp_arrays[id_] = z = zarr.open(
                str(tmp.name), shape=shape, dtype=dtype
            )
            fname = self._mda_meta.file_name if self._mda_meta.should_save else "HCS"

            layer = self.viewer.add_image(z, name=f"{fname}_{id_}")

            # add metadata to layer
            # storing event.index in addition to channel.config because it's
            # possible to have two of the same channel in one sequence.
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["well"] = pos

    @ensure_main_thread
    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):
        meta = self._mda_meta
        axis_order = list(event_indices(event))

        if meta.mode == "mda":

            # Remove 'c' from idxs if we are splitting channels
            # also prepare the channel suffix that we use for keeping track of arrays
            channel = ""
            if meta.split_channels:
                channel = f"_{event.channel.config}"
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

        elif meta.mode == "explorer":

            if meta.translate_explorer:

                with contextlib.suppress(ValueError):
                    axis_order.remove("p")

                # get the actual index of this image into the array
                # add it to the zarr store
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
                fname = (
                    self._mda_meta.file_name if self._mda_meta.should_save else "Exp"
                )
                layer = self.viewer.layers[f"{fname}_{layer_name}"]
                if (layer.translate[-2], layer.translate[-1]) != (y, x):
                    layer.translate = (y, x)
                layer.metadata["translate"] = True
                layer.metadata["pos"] = (event.x_pos, event.y_pos, event.z_pos)

                # link layers after translation
                for group in layergroups.values():
                    link_layers(group)

                # move the viewer step to the most recently added image
                for a, v in enumerate(im_idx):
                    self.viewer.dims.set_point(a, v)

                layer.reset_contrast_limits()

                zoom_out_factor = (
                    self.explorer.scan_size_r
                    if self.explorer.scan_size_r >= self.explorer.scan_size_c
                    else self.explorer.scan_size_c
                )
                self.viewer.camera.zoom = 1 / zoom_out_factor
                self.viewer.reset_view()

            else:
                # get the actual index of this image into the array
                # add it to the zarr store
                im_idx = tuple(event.index[k] for k in axis_order)
                # add index of this image to the zarr store
                self._mda_temp_arrays[str(event.sequence.uid)][im_idx] = image

                # move the viewer step to the most recently added image
                for a, v in enumerate(im_idx):
                    self.viewer.dims.set_point(a, v)

        elif meta.mode == "hcs":

            if self.multi_pos == 0:
                axis_order.remove("p")

            # get the actual index of this image into the array
            # add it to the zarr store
            im_idx = ()
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

            layer.reset_contrast_limits()

            self.viewer.reset_view()

    def _on_mda_finished(self, sequence: useq.MDASequence) -> None:
        """Save layer and add increment to save name."""
        meta = self._mda_meta
        meta = _mda_meta.SEQUENCE_META.pop(sequence, self._mda_meta)
        save_sequence(sequence, self.viewer.layers, meta)
        # reactivate gui when mda finishes.
        self._set_enabled(True)

    # def _get_event_explorer(self, viewer, event):
    #     if not self.explorer.isVisible():
    #         return
    #     if self._mmc.getPixelSizeUm() > 0:
    #         width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
    #         height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

    #         x = viewer.cursor.position[-1] * self._mmc.getPixelSizeUm()
    #         y = viewer.cursor.position[-2] * self._mmc.getPixelSizeUm() * (-1)

    #         # to match position coordinates with center of the image
    #         x = f"{x - ((width / 2) * self._mmc.getPixelSizeUm()):.1f}"
    #         y = f"{y - ((height / 2) * self._mmc.getPixelSizeUm() * (-1)):.1f}"

    #     else:
    #         x, y = "None", "None"

    #     self.explorer.x_lineEdit.setText(x)
    #     self.explorer.y_lineEdit.setText(y)

    def _update_live_exp(self, camera: str, exposure: float):
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

    def _get_roi_layer(self) -> napari.layers.shapes.shapes.Shapes:
        for layer in self.viewer.layers:
            if layer.metadata.get("layer_id"):
                return layer

    def _on_roi_info(
        self, start_x: int, start_y: int, width: int, height: int, mode: str = ""
    ) -> None:

        layers = {layer.name for layer in self.viewer.layers}
        if "preview" not in layers:
            self._mmc.snap()

        if mode == "Full":
            self._on_crop_btn()
            return

        try:
            cam_roi_layer = self._get_roi_layer()
            cam_roi_layer.data = self._set_cam_roi_shape(
                start_x, start_y, width, height
            )
        except AttributeError:
            cam_roi_layer = self.viewer.add_shapes(name="set_cam_ROI")
            cam_roi_layer.metadata["layer_id"] = "set_cam_ROI"
            cam_roi_layer.data = self._set_cam_roi_shape(
                start_x, start_y, width, height
            )

        cam_roi_layer.mode = "select"
        self.viewer.reset_view()

    def _set_cam_roi_shape(
        self, start_x: int, start_y: int, width: int, height: int
    ) -> List[list]:
        return [
            [start_y, start_x],
            [start_y, width + start_x],
            [height + start_y, width + start_x],
            [height + start_y, start_x],
        ]

    def _on_crop_btn(self):
        with contextlib.suppress(Exception):
            cam_roi_layer = self._get_roi_layer()
            self.viewer.layers.remove(cam_roi_layer)
        self.viewer.reset_view()

    def _update_cam_roi_layer(self, layer, event) -> None:  # type: ignore

        active_layer = self.viewer.layers.selection.active
        if not isinstance(active_layer, napari.layers.shapes.shapes.Shapes):
            return

        if active_layer.metadata.get("layer_id") != "set_cam_ROI":
            return

        # on mouse pressed
        dragged = False
        yield
        # on mouse move
        while event.type == "mouse_move":
            dragged = True
            yield
        # on mouse release
        if dragged:
            if not active_layer.data:
                return
            data = active_layer.data[-1]

            x_max = self.tab_wdg.cam_wdg.chip_size_x
            y_max = self.tab_wdg.cam_wdg.chip_size_y

            x = round(data[0][1])
            y = round(data[0][0])
            width = round(data[1][1] - x)
            height = round(data[2][0] - y)

            # change shape if out of cam area
            if x + width >= x_max:
                x = x - ((x + width) - x_max)
            if y + height >= y_max:
                y = y - ((y + height) - y_max)

            cam = self._mmc.getCameraDevice()
            self._mmc.events.roiSet.emit(cam, x, y, width, height)

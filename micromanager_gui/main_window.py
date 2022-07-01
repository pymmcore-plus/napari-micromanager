from __future__ import annotations

import atexit
import contextlib
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple

import napari
import numpy as np
import zarr
from napari.experimental import link_layers
from pymmcore_plus._util import find_micromanager
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QTimer
from qtpy.QtGui import QColor, QIcon
from superqt.utils import create_worker, ensure_main_thread
from useq import MDASequence

from . import _core, _mda
from ._camera_roi import _CameraROI
from ._core_widgets import PropertyBrowser
from ._gui_objects._mm_widget import MicroManagerWidget
from ._saving import save_sequence
from ._util import event_indices

if TYPE_CHECKING:
    from typing import Dict

    import napari.layers
    import napari.viewer
    import useq
    from pymmcore_plus.core.events import QCoreSignaler
    from pymmcore_plus.mda import PMDAEngine

ICONS = Path(__file__).parent / "icons"
CAM_ICON = QIcon(str(ICONS / "vcam.svg"))
CAM_STOP_ICON = QIcon(str(ICONS / "cam_stop.svg"))


class MainWindow(MicroManagerWidget):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(self, viewer: napari.viewer.Viewer, remote=False):
        super().__init__()

        # create connection to mmcore server or process-local variant
        self._mmc = _core.get_core_singleton(remote)

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

        self.cam_roi = _CameraROI(
            self.viewer,
            self._mmc,
            self.cam_wdg.cam_roi_combo,
            self.cam_wdg.crop_btn,
        )

        self.viewer.layers.events.connect(self._update_max_min)
        self.viewer.layers.selection.events.active.connect(self._update_max_min)
        self.viewer.dims.events.current_step.connect(self._update_max_min)
        self.viewer.mouse_drag_callbacks.append(self._get_event_explorer)

        self._add_menu()

    def _add_menu(self):
        w = getattr(self.viewer, "__wrapped__", self.viewer).window  # don't do this.
        self._menu = QtW.QMenu("&Micro-Manager", w._qt_window)

        action = self._menu.addAction("Device Property Browser...")
        action.triggered.connect(self._show_prop_browser)

        bar = w._qt_window.menuBar()
        bar.insertMenu(list(bar.actions())[-1], self._menu)

    def _show_prop_browser(self):
        if not hasattr(self, "_prop_browser"):
            self._prop_browser = PropertyBrowser(self._mmc, self)
        self._prop_browser.show()
        self._prop_browser.raise_()

    def _on_system_cfg_loaded(self):
        if len(self._mmc.getLoadedDevices()) > 1:
            self._set_enabled(True)

    def _set_enabled(self, enabled):
        if self._mmc.getCameraDevice():
            self._camera_group_wdg(enabled)
            self.tab_wdg.snap_live_tab.setEnabled(enabled)
            self.tab_wdg.snap_live_tab.setEnabled(enabled)
        else:
            self._camera_group_wdg(False)
            self.tab_wdg.snap_live_tab.setEnabled(False)
            self.tab_wdg.snap_live_tab.setEnabled(False)

        self.illum_btn.setEnabled(enabled)

        self.mda._set_enabled(enabled)
        if self._mmc.getXYStageDevice():
            self.explorer._set_enabled(enabled)
        else:
            self.explorer._set_enabled(False)

    def _camera_group_wdg(self, enabled):
        self.cam_wdg.setEnabled(enabled)

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
        oldEngine.events.frameReady.connect(self._on_mda_frame)
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)

        newEngine.events.frameReady.connect(self._on_mda_frame)
        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)

    @ensure_main_thread
    def _on_mda_started(self, sequence: useq.MDASequence):
        """Create temp folder and block gui when mda starts."""
        self._set_enabled(False)

        self._mda_meta = _mda.SEQUENCE_META.get(sequence, _mda.SequenceMeta())
        if self._mda_meta.mode == "explorer":
            # shortcircuit - nothing to do
            return
        elif self._mda_meta.mode == "":
            # originated from user script - assume it's an mda
            self._mda_meta.mode = "mda"

        # work out what the shapes of the layers will be
        # this depends on whether the user selected Split Channels or not
        shape, channels, labels = self._interpret_split_channels(sequence)

        # acutally create the viewer layers backed by zarr stores
        self._add_mda_channel_layers(tuple(shape), channels, sequence)

        # set axis_labels after adding the images to ensure that the dims exist
        self.viewer.dims.axis_labels = labels

    def _interpret_split_channels(
        self, sequence: MDASequence
    ) -> Tuple[List[int], List[str], List[str]]:
        """Determine the shape of layers and the dimension labels.

        ...based on whether we are splitting on channels
        """
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

    @ensure_main_thread
    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):
        meta = self._mda_meta
        if meta.mode == "mda":
            axis_order = list(event_indices(event))

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

            seq = event.sequence

            meta = _mda.SEQUENCE_META.get(seq) or _mda.SequenceMeta()
            if meta.mode != "explorer":
                return

            x = event.x_pos / self.explorer.pixel_size
            y = event.y_pos / self.explorer.pixel_size * (-1)

            pos_idx = event.index["p"]
            file_name = meta.file_name if meta.should_save else "Exp"
            ch_name = event.channel.config
            ch_id = event.index["c"]
            layer_name = f"Pos{pos_idx:03d}_{file_name}_{ch_name}_idx{ch_id}"

            _metadata = dict(
                useq_sequence=seq,
                uid=seq.uid,
                scan_coord=(y, x),
                scan_position=f"Pos{pos_idx:03d}",
                ch_name=ch_name,
                ch_id=ch_id,
            )
            self.viewer.add_image(
                image,
                name=layer_name,
                blending="additive",
                translate=(y, x),
                metadata=_metadata,
            )

            zoom_out_factor = (
                self.explorer.scan_size_r
                if self.explorer.scan_size_r >= self.explorer.scan_size_c
                else self.explorer.scan_size_c
            )
            self.viewer.camera.zoom = 1 / zoom_out_factor
            self.viewer.reset_view()

    def _on_mda_finished(self, sequence: useq.MDASequence):
        """Save layer and add increment to save name."""
        meta = _mda.SEQUENCE_META.get(sequence) or _mda.SequenceMeta()
        seq_uid = sequence.uid
        if meta.mode == "explorer":

            layergroups = defaultdict(set)
            for lay in self.viewer.layers:
                if lay.metadata.get("uid") == seq_uid:
                    key = f"{lay.metadata['ch_name']}_idx{lay.metadata['ch_id']}"
                    layergroups[key].add(lay)
            for group in layergroups.values():
                link_layers(group)
        meta = _mda.SEQUENCE_META.pop(sequence, self._mda_meta)
        save_sequence(sequence, self.viewer.layers, meta)
        # reactivate gui when mda finishes.
        self._set_enabled(True)

    def _get_event_explorer(self, viewer, event):
        if not self.explorer.isVisible():
            return
        if self._mmc.getPixelSizeUm() > 0:
            width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
            height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

            x = viewer.cursor.position[-1] * self._mmc.getPixelSizeUm()
            y = viewer.cursor.position[-2] * self._mmc.getPixelSizeUm() * (-1)

            # to match position coordinates with center of the image
            x = f"{x - ((width / 2) * self._mmc.getPixelSizeUm()):.1f}"
            y = f"{y - ((height / 2) * self._mmc.getPixelSizeUm() * (-1)):.1f}"

        else:
            x, y = "None", "None"

        self.explorer.x_lineEdit.setText(x)
        self.explorer.y_lineEdit.setText(y)

    def _update_live_exp(self, camera: str, exposure: float):
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

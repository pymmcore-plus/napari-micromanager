from __future__ import annotations

import atexit
import contextlib
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, Any, List, Tuple

import napari
import numpy as np
import zarr
from napari.experimental import link_layers, unlink_layers
from pymmcore_plus import CMMCorePlus
from pymmcore_plus._util import find_micromanager
from pymmcore_widgets import PropertyBrowser
from qtpy.QtCore import QTimer
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QMenu, QSizePolicy
from superqt.utils import create_worker, ensure_main_thread
from useq import MDASequence

from . import _mda_meta
from ._gui_objects._mm_widget import MicroManagerWidget
from ._saving import save_sequence
from ._util import event_indices

if TYPE_CHECKING:
    from typing import Dict

    import napari.layers
    import napari.viewer
    import useq


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
        sizepolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.tab_wdg.setSizePolicy(sizepolicy)

        self.streaming_timer: QTimer | None = None

        self._mda_meta: _mda_meta.SequenceMeta | None = None

        # disable gui
        self._set_enabled(False)

        # connect mmcore signals
        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._mmc.events.exposureChanged.connect(self._update_live_exp)

        self._mmc.events.imageSnapped.connect(self.update_viewer)
        self._mmc.events.imageSnapped.connect(self._stop_live)

        # mda events
        self._mmc.mda.events.frameReady.connect(self._on_mda_frame)
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)

        self._mmc.events.continuousSequenceAcquisitionStarted.connect(self._start_live)
        self._mmc.events.sequenceAcquisitionStopped.connect(self._stop_live)

        # connect metadata info
        self.explorer.metadataInfo.connect(self._on_meta_info)
        self.mda.metadataInfo.connect(self._on_meta_info)

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
        self.viewer.layers.selection.events.connect(self._update_max_min)
        self.viewer.dims.events.current_step.connect(self._update_max_min)

        self._add_menu()

    def _add_menu(self):
        w = getattr(self.viewer, "__wrapped__", self.viewer).window  # don't do this.
        self._menu = QMenu("&Micro-Manager", w._qt_window)

        action = self._menu.addAction("Device Property Browser...")
        action.triggered.connect(self._show_prop_browser)

        bar = w._qt_window.menuBar()
        bar.insertMenu(list(bar.actions())[-1], self._menu)

    def _show_prop_browser(self):
        if not hasattr(self, "_prop_browser"):
            self._prop_browser = PropertyBrowser(mmcore=self._mmc, parent=self)
        self._prop_browser.show()
        self._prop_browser.raise_()

    def _on_system_cfg_loaded(self):
        if len(self._mmc.getLoadedDevices()) > 1:
            self._set_enabled(True)

    def _on_meta_info(
        self, meta: _mda_meta.SequenceMeta, sequence: MDASequence
    ) -> None:
        self._mda_meta = _mda_meta.SEQUENCE_META.get(sequence, meta)

    def _set_enabled(self, enabled):
        self.illum_btn.setEnabled(enabled)

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

        preview_layer.metadata["mode"] = "preview"

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

    @ensure_main_thread
    def _on_mda_started(self, sequence: useq.MDASequence):
        """Create temp folder and block gui when mda starts."""
        if not self._mda_meta:
            return

        self._set_enabled(False)

        # pause acquisition until zarr layer(s) is(are) added
        self._mmc.mda.toggle_pause()

        if self._mda_meta.mode in ["mda", ""]:
            # work out what the shapes of the mda layers will be
            # depends on whether the user selected Split Channels or not
            sh_ch_lbl = self._interpret_split_channels(sequence)
            if sh_ch_lbl is None:
                return
            shape, channels, labels = sh_ch_lbl
            # create the viewer layers backed by zarr stores
            self._add_mda_channel_layers(tuple(shape), channels, sequence)

        elif self._mda_meta.mode == "explorer":

            if self._mda_meta.translate_explorer:
                shape, positions, labels = self._interpret_explorer_positions(sequence)
                self._add_explorer_positions_layers(tuple(shape), positions, sequence)
            else:
                sh_ch_lbl = self._interpret_split_channels(sequence)
                if sh_ch_lbl is None:
                    return
                shape, channels, labels = sh_ch_lbl
                self._add_mda_channel_layers(tuple(shape), channels, sequence)

        # set axis_labels after adding the images to ensure that the dims exist
        self.viewer.dims.axis_labels = labels

        # resume acquisition after zarr layer(s) is(are) added
        if [i for i in self.viewer.layers if i.metadata.get("uid") == sequence.uid]:
            self._mmc.mda.toggle_pause()

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
    ) -> Tuple[List[int], List[str], List[str]] | None:
        """
        Determine shape, channels and labels.

        ...based on whether we are splitting on channels
        """
        if not self._mda_meta:
            return None

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

    def _add_mda_channel_layers(
        self, shape: Tuple[int, ...], channels: List[str], sequence: MDASequence
    ):
        """Create Zarr stores to back MDA and display as new viewer layer(s).

        If splitting on Channels then channels will look like ["BF", "GFP",...]
        and if we do not split on channels it will look like [""] and only one
        layer/zarr store will be created.
        """
        if not self._mda_meta:
            return

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
            layer.visible = False

            # add metadata to layer
            layer.metadata["mode"] = self._mda_meta.mode
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["ch_id"] = f"{channel}"

    def _add_explorer_positions_layers(
        self, shape: Tuple[int, ...], positions: List[str], sequence: MDASequence
    ) -> None:
        """Create Zarr stores to back Explorer and display as new viewer layer(s)."""
        if not self._mda_meta:
            return

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
            layer.visible = False

            # add metadata to layer
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

    @ensure_main_thread
    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):

        if not self._mda_meta:
            return

        if self._mda_meta.mode == "mda":
            self._mda_acquisition(image, event, self._mda_meta)
        elif self._mda_meta.mode == "explorer":
            if self._mda_meta.translate_explorer:
                self._explorer_acquisition_translate(image, event, self._mda_meta)
            else:
                self._explorer_acquisition_stack(image, event)

    def _mda_acquisition(
        self, image: np.ndarray, event: useq.MDAEvent, meta: _mda_meta.SequenceMeta
    ) -> None:

        if not self._mda_meta:
            return

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
        # this seems to work better than self.viewer.dims.set_point(a, v)
        cs = list(self.viewer.dims.current_step)
        for a, v in enumerate(im_idx):
            cs[a] = v
        self.viewer.dims.current_step = tuple(cs)

        # display
        fname = self._mda_meta.file_name if self._mda_meta.should_save else "Exp"
        layer_name = f"{fname}_{event.sequence.uid}{channel}"
        layer = self.viewer.layers[layer_name]
        if not layer.visible:
            layer.visible = True
        # layer.reset_contrast_limits()

    def _explorer_acquisition_stack(
        self, image: np.ndarray, event: useq.MDAEvent
    ) -> None:

        if not self._mda_meta:
            return

        axis_order = list(event_indices(event))
        im_idx = tuple(event.index[k] for k in axis_order)
        self._mda_temp_arrays[str(event.sequence.uid)][im_idx] = image

        cs = list(self.viewer.dims.current_step)
        for a, v in enumerate(im_idx):
            cs[a] = v
        self.viewer.dims.current_step = tuple(cs)

        fname = self._mda_meta.file_name if self._mda_meta.should_save else "Exp"
        layer = self.viewer.layers[f"{fname}_{event.sequence.uid}"]
        if not layer.visible:
            layer.visible = True
        layer.reset_contrast_limits()

    def _explorer_acquisition_translate(
        self, image: np.ndarray, event: useq.MDAEvent, meta: _mda_meta.SequenceMeta
    ) -> None:

        if not self._mda_meta:
            return

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

        # link layers after translation
        for group in layergroups.values():
            link_layers(group)

        # for a, v in enumerate(im_idx):
        #     self.viewer.dims.set_point(a, v)
        cs = list(self.viewer.dims.current_step)
        for a, v in enumerate(im_idx):
            cs[a] = v
        self.viewer.dims.current_step = tuple(cs)

        # to fix a bug in display (e.g. 3x3 grid)
        layer.visible = False
        layer.visible = True

        zoom_out_factor = (
            self.explorer.scan_size_r
            if self.explorer.scan_size_r >= self.explorer.scan_size_c
            else self.explorer.scan_size_c
        )
        self.viewer.camera.zoom = 1 / zoom_out_factor
        self.viewer.reset_view()

    def _on_mda_finished(self, sequence: useq.MDASequence):

        # reactivate gui when mda finishes.
        self._set_enabled(True)

        if not self._mda_meta:
            return

        # Save layer and add increment to save name.
        meta = self._mda_meta
        meta = _mda_meta.SEQUENCE_META.pop(sequence, self._mda_meta)
        save_sequence(sequence, self.viewer.layers, meta)

    def _update_live_exp(self, camera: str, exposure: float):
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

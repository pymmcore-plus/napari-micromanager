from __future__ import annotations

import atexit
import contextlib
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import napari
import numpy as np
import zarr
from napari.experimental import link_layers, unlink_layers
from pymmcore_plus import CMMCorePlus
from pymmcore_plus._util import find_micromanager
from qtpy.QtCore import QTimer
from qtpy.QtGui import QColor
from superqt.utils import create_worker, ensure_main_thread
from useq import MDAEvent, MDASequence

from . import _mda_meta
from ._gui_objects._toolbar import MicroManagerToolbar
from ._saving import save_sequence
from ._util import event_indices

if TYPE_CHECKING:

    import napari.layers
    import napari.viewer
    import useq

    class ActiveMDAEvent(MDAEvent):
        """Event that has been assigned a sequence."""

        sequence: MDASequence


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(self, viewer: napari.viewer.Viewer) -> None:
        super().__init__(viewer)

        # create connection to mmcore server or process-local variant
        self._mmc = CMMCorePlus.instance()

        self.viewer = viewer
        # self._dock_widgets: dict[str, QtViewerDockWidget] = {}

        adapter_path = find_micromanager()
        if not adapter_path:
            raise RuntimeError(
                "Could not find micromanager adapters. Please run "
                "`python -m pymmcore_plus.install` or install manually and set "
                "MICROMANAGER_PATH."
            )

        self.streaming_timer: QTimer | None = None

        # connect mmcore signals
        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        # self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._mmc.events.exposureChanged.connect(self._update_live_exp)

        self._mmc.events.imageSnapped.connect(self.update_viewer)
        self._mmc.events.imageSnapped.connect(self._stop_live)

        # mda events
        self._mmc.mda.events.frameReady.connect(self._on_mda_frame)
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)

        self._mmc.events.continuousSequenceAcquisitionStarted.connect(self._start_live)
        self._mmc.events.sequenceAcquisitionStopped.connect(self._stop_live)

        # mapping of str `str(sequence.uid) + channel` -> zarr.Array for each layer
        # being added during an MDA
        self._mda_temp_arrays: dict[str, zarr.Array] = {}
        # mapping of str `str(sequence.uid) + channel` -> temporary directory where
        # the zarr.Array is stored
        self._mda_temp_files: dict[str, tempfile.TemporaryDirectory] = {}

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

        # add minmax dockwidget
        self.viewer.window.add_dock_widget(self.minmax, name="MinMax", area="left")

    @ensure_main_thread  # type: ignore [misc]
    def update_viewer(self, data: np.ndarray | None = None) -> None:
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

    def _update_max_min(self, event: Any = None) -> None:

        min_max_txt = ""
        layers: list[napari.layers.Image] = [
            lr
            for lr in self.viewer.layers.selection
            if isinstance(lr, napari.layers.Image) and lr.visible
        ]

        if not layers:
            self.minmax.max_min_val_label.setText(min_max_txt)
            return

        for layer in layers:
            col = layer.colormap.name
            if col not in QColor.colorNames():
                col = "gray"
            # min and max of current slice
            min_max_show = tuple(layer._calc_data_range(mode="slice"))
            min_max_txt += f'<font color="{col}">{min_max_show}</font>'

        self.minmax.max_min_val_label.setText(min_max_txt)

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

    @ensure_main_thread  # type: ignore [misc]
    def _on_mda_started(self, sequence: useq.MDASequence) -> None:
        """Create temp folder and block gui when mda starts."""
        meta = _mda_meta.SEQUENCE_META.get(sequence)
        if meta is None:
            return

        # pause acquisition until zarr layer(s) is(are) added
        self._mmc.mda.toggle_pause()

        if meta.mode in ["mda", ""]:
            # work out what the shapes of the mda layers will be
            # depends on whether the user selected Split Channels or not
            sh_ch_lbl = self._interpret_split_channels(sequence, meta)
            if sh_ch_lbl is None:
                return
            shape, channels, labels = sh_ch_lbl
            # create the viewer layers backed by zarr stores
            self._add_mda_channel_layers(tuple(shape), channels, sequence, meta)

        elif meta.mode == "explorer":

            if meta.translate_explorer:
                shape, positions, labels = self._interpret_explorer_positions(sequence)
                self._add_explorer_positions_layers(
                    tuple(shape), positions, sequence, meta
                )
            else:
                sh_ch_lbl = self._interpret_split_channels(sequence, meta)
                if sh_ch_lbl is None:
                    return
                shape, channels, labels = sh_ch_lbl
                self._add_mda_channel_layers(tuple(shape), channels, sequence, meta)

        # set axis_labels after adding the images to ensure that the dims exist
        self.viewer.dims.axis_labels = labels

        # resume acquisition after zarr layer(s) is(are) added
        if [i for i in self.viewer.layers if i.metadata.get("uid") == sequence.uid]:
            self._mmc.mda.toggle_pause()

    def _get_shape_and_labels(
        self, sequence: MDASequence
    ) -> tuple[list[str], list[int]]:
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

    def _get_channel_name_with_index(self, sequence: MDASequence) -> list[str]:
        """Store index in addition to channel.config.

        It is possible to have two or more of the same channel in one sequence.
        """
        channels = []
        for i in sequence.iter_events():
            if i.channel:
                ch = f"_{i.channel.config}_{i.index['c']:03d}"
                if ch not in channels:
                    channels.append(ch)
        return channels

    def _interpret_split_channels(
        self, sequence: MDASequence, meta: _mda_meta.SequenceMeta
    ) -> tuple[list[int], list[str], list[str]] | None:
        """
        Determine shape, channels and labels.

        ...based on whether we are splitting on channels
        """
        labels, shape = self._get_shape_and_labels(sequence)
        if meta.split_channels:
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
    ) -> tuple[list[int], list[str], list[str]]:
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
        self,
        shape: tuple[int, ...],
        channels: list[str],
        sequence: MDASequence,
        meta: _mda_meta.SequenceMeta,
    ) -> None:
        """Create Zarr stores to back MDA and display as new viewer layer(s).

        If splitting on Channels then channels will look like ["BF", "GFP",...]
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
            fname = meta.file_name if meta.should_save else "Exp"
            layer = self.viewer.add_image(z, name=f"{fname}_{id_}", blending="additive")
            layer.visible = False

            # add metadata to layer
            layer.metadata["mode"] = meta.mode
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["ch_id"] = f"{channel}"

    def _add_explorer_positions_layers(
        self,
        shape: tuple[int, ...],
        positions: list[str],
        sequence: MDASequence,
        meta: _mda_meta.SequenceMeta,
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
            fname = meta.file_name if meta.should_save else "Exp"
            layer = self.viewer.add_image(z, name=f"{fname}_{id_}", blending="additive")
            layer.visible = False

            # add metadata to layer
            layer.metadata["mode"] = meta.mode
            layer.metadata["useq_sequence"] = sequence
            layer.metadata["uid"] = sequence.uid
            layer.metadata["grid"] = pos.split("_")[-3]
            layer.metadata["grid_pos"] = pos.split("_")[-2]

    def _get_defaultdict_layers(self, event: ActiveMDAEvent) -> defaultdict[Any, set]:
        layergroups = defaultdict(set)
        for lay in self.viewer.layers:
            if lay.metadata.get("uid") == event.sequence.uid:
                key = lay.metadata.get("grid")[:8]
                layergroups[key].add(lay)
        return layergroups

    @ensure_main_thread  # type: ignore [misc]
    def _on_mda_frame(self, image: np.ndarray, event: ActiveMDAEvent) -> None:
        meta = _mda_meta.SEQUENCE_META.get(event.sequence)
        if meta is None:
            return

        if meta.mode == "mda":
            self._mda_acquisition(image, event, meta)
        elif meta.mode == "explorer":
            if meta.translate_explorer:
                self._explorer_acquisition_translate(image, event, meta)
            else:
                self._explorer_acquisition_stack(image, event, meta)

    def _mda_acquisition(
        self, image: np.ndarray, event: ActiveMDAEvent, meta: _mda_meta.SequenceMeta
    ) -> None:

        axis_order = list(event_indices(event))
        # Remove 'c' from idxs if we are splitting channels
        # also prepare the channel suffix that we use for keeping track of arrays
        channel = ""
        if meta.split_channels and event.channel:
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
        fname = meta.file_name if meta.should_save else "Exp"
        layer_name = f"{fname}_{event.sequence.uid}{channel}"
        layer = self.viewer.layers[layer_name]
        if not layer.visible:
            layer.visible = True
        # layer.reset_contrast_limits()

    def _explorer_acquisition_stack(
        self, image: np.ndarray, event: ActiveMDAEvent, meta: _mda_meta.SequenceMeta
    ) -> None:

        axis_order = list(event_indices(event))
        im_idx = tuple(event.index[k] for k in axis_order)
        self._mda_temp_arrays[str(event.sequence.uid)][im_idx] = image

        cs = list(self.viewer.dims.current_step)
        for a, v in enumerate(im_idx):
            cs[a] = v
        self.viewer.dims.current_step = tuple(cs)

        fname = meta.file_name if meta.should_save else "Exp"
        layer = self.viewer.layers[f"{fname}_{event.sequence.uid}"]
        if not layer.visible:
            layer.visible = True
        layer.reset_contrast_limits()

    def _explorer_acquisition_translate(
        self, image: np.ndarray, event: ActiveMDAEvent, meta: _mda_meta.SequenceMeta
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
        fname = meta.file_name if meta.should_save else "Exp"
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
            meta.scan_size_r
            if meta.scan_size_r >= meta.scan_size_c
            else meta.scan_size_c
        )
        self.viewer.camera.zoom = 1 / zoom_out_factor
        self.viewer.reset_view()

    def _on_mda_finished(self, sequence: useq.MDASequence) -> None:
        # Save layer and add increment to save name.
        meta = _mda_meta.SEQUENCE_META.pop(sequence, None)
        if meta is not None:
            save_sequence(sequence, self.viewer.layers, meta)

    def _update_live_exp(self, camera: str, exposure: float) -> None:
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

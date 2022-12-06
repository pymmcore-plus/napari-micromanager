from __future__ import annotations

import contextlib
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable

import napari
import numpy as np
import zarr
from napari.experimental import link_layers, unlink_layers
from pymmcore_plus import CMMCorePlus
from superqt.utils import ensure_main_thread
from useq import MDAEvent, MDASequence

from ._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from ._saving import save_sequence

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer
    from pymmcore_plus.core.events._protocol import PSignalInstance

    class ActiveMDAEvent(MDAEvent):
        """Event that has been assigned a sequence."""

        sequence: MDASequence


class _NapariMDAHandler:
    """Object mediating events between an in-progress MDA and the napari viewer.

    It is typically created by the MainWindow, but could conceivably live alone.

    Parameters
    ----------
    mmcore : CMMCorePlus
        The Micro-Manager core instance.
    viewer : napari.viewer.Viewer
        The napari viewer instance.
    """

    def __init__(self, mmcore: CMMCorePlus, viewer: napari.viewer.Viewer) -> None:
        self._mmc = mmcore
        self.viewer = viewer

        # mapping of str `str(sequence.uid) + channel` -> zarr.Array for each layer
        # being added during an MDA
        self._mda_temp_arrays: dict[str, zarr.Array] = {}
        # mapping of str `str(sequence.uid) + channel` -> temporary directory where
        # the zarr.Array is stored
        self._mda_temp_files: dict[str, tempfile.TemporaryDirectory] = {}

        # Add all core connections to this list.  This makes it easy to disconnect
        # from core when this widget is closed.
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self._mmc.mda.events.frameReady, self._on_mda_frame),
            (self._mmc.mda.events.sequenceStarted, self._on_mda_started),
            (self._mmc.mda.events.sequenceFinished, self._on_mda_finished),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

    def _cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        for z in self._mda_temp_arrays.values():
            z.store.close()
        for v in self._mda_temp_files.values():
            with contextlib.suppress(NotADirectoryError):
                v.cleanup()

    @ensure_main_thread  # type: ignore [misc]
    def _on_mda_started(self, sequence: MDASequence) -> None:
        """Create temp folder and block gui when mda starts."""
        meta: SequenceMeta | None = sequence.metadata.get(SEQUENCE_META_KEY)
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
        labels, shape = zip(*((k, v) for k, v in sequence.sizes.items() if v > 0))
        labels = labels + ("y", "x")
        shape = shape + (self._mmc.getImageHeight(), self._mmc.getImageWidth())
        return list(labels), list(shape)

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
        self, sequence: MDASequence, meta: SequenceMeta
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
        meta: SequenceMeta,
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

            # set layer scale
            layer.scale = self._get_scale_from_sequence(
                sequence, layer.data.shape, meta
            )

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
        meta: SequenceMeta,
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

            # set layer scale
            layer.scale = self._get_scale_from_sequence(
                sequence, layer.data.shape, meta
            )

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

    def _get_scale_from_sequence(
        self, sequence: MDASequence, layer_shape: tuple[int], meta: SequenceMeta
    ) -> list[float]:
        """Calculate and return the layer scale.

        ...using pixel size, layer shape and the MDASequence z info.
        """
        scale = [1.0] * len(layer_shape)
        scale[-2:] = [self._mmc.getPixelSizeUm()] * 2
        if (index := sequence.used_axes.find("z")) > -1:
            if meta.split_channels and sequence.used_axes.find("c") < index:
                index -= 1
            scale[index] = getattr(sequence.z_plan, "step", 1)
        return scale

    @ensure_main_thread  # type: ignore [misc]
    def _on_mda_frame(self, image: np.ndarray, event: ActiveMDAEvent) -> None:
        meta: SequenceMeta | None = event.sequence.metadata.get(SEQUENCE_META_KEY)
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
        self, image: np.ndarray, event: ActiveMDAEvent, meta: SequenceMeta
    ) -> None:

        axis_order = list(event.sequence.used_axes)
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
        self, image: np.ndarray, event: ActiveMDAEvent, meta: SequenceMeta
    ) -> None:

        im_idx = tuple(event.index[k] for k in event.sequence.used_axes)
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
        self, image: np.ndarray, event: ActiveMDAEvent, meta: SequenceMeta
    ) -> None:
        im_idx = tuple(event.index[k] for k in event.sequence.used_axes if k != "p")
        layer_name = f"{event.pos_name}_{event.sequence.uid}"
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

    def _on_mda_finished(self, sequence: MDASequence) -> None:
        # Save layer and add increment to save name.
        if (meta := sequence.metadata.get(SEQUENCE_META_KEY)) is not None:
            save_sequence(sequence, self.viewer.layers, meta)

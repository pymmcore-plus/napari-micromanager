from __future__ import annotations

import contextlib
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, cast

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
    from uuid import UUID

    import napari.layers
    import napari.viewer
    from pymmcore_plus.core.events._protocol import PSignalInstance
    from typing_extensions import NotRequired, TypedDict

    class ActiveMDAEvent(MDAEvent):
        """Event that has been assigned a sequence."""

        sequence: MDASequence

    # TODO: the keys are accurate, but currently this is at the top level layer.metadata
    # we should nest it under a napari_micromanager key
    class LayerMeta(TypedDict):
        """Metadata that we add to layer.metadata."""

        mode: str
        useq_sequence: MDASequence
        uid: UUID
        grid: NotRequired[str]
        grid_pos: NotRequired[str]
        ch_id: NotRequired[str]
        translate: NotRequired[bool]


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

        # mapping of id -> (zarr.Array, temporary directory) for each layer created
        self._tmp_arrays: dict[str, tuple[zarr.Array, tempfile.TemporaryDirectory]] = {}

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
        for z, v in self._tmp_arrays.values():
            z.store.close()
            with contextlib.suppress(NotADirectoryError):
                v.cleanup()

    @ensure_main_thread  # type: ignore [misc]
    def _on_mda_started(self, sequence: MDASequence) -> None:
        """Create temp folder and block gui when mda starts."""
        meta: SequenceMeta | None = sequence.metadata.get(SEQUENCE_META_KEY)
        if meta is None:
            # this is not an MDA we started
            # TODO: should we handle this with some sane defaults?
            return

        # pause acquisition until zarr layer(s) are added
        self._mmc.mda.toggle_pause()

        # determine the new layers that need to be created for this experiment
        # (based on the sequence mode, and whether we're splitting C/P, etc.)
        axis_labels, layers_to_create = _determine_sequence_layers(sequence)
        yx_shape = [self._mmc.getImageHeight(), self._mmc.getImageWidth()]

        # now create a zarr array in a temporary directory for each layer
        for (id_, shape, kwargs) in layers_to_create:
            tmp = tempfile.TemporaryDirectory()
            dtype = f"uint{self._mmc.getImageBitDepth()}"

            # create the zarr array and add it to the viewer
            z = zarr.open(str(tmp.name), shape=shape + yx_shape, dtype=dtype)
            fname = meta.file_name if meta.should_save else "Exp"
            self._create_empty_image_layer(z, f"{fname}_{id_}", sequence, **kwargs)

            # store the zarr array and temporary directory for later cleanup
            self._tmp_arrays[id_] = (z, tmp)

        # set axis_labels after adding the images to ensure that the dims exist
        self.viewer.dims.axis_labels = axis_labels

        # resume acquisition after zarr layer(s) is(are) added
        # FIXME: this isn't in an event loop... so shouldn't we just call toggle_pause?
        for i in self.viewer.layers:
            if i.metadata.get("uid") == sequence.uid:
                self._mmc.mda.toggle_pause()
                return

    @ensure_main_thread  # type: ignore [misc]
    def _on_mda_frame(self, image: np.ndarray, event: ActiveMDAEvent) -> None:
        """Called on the `frameReady` event from the core."""
        meta: SequenceMeta | None = event.sequence.metadata.get(SEQUENCE_META_KEY)
        if meta is None:
            return

        if meta.mode in ("mda", ""):
            self._add_frame_to_mda_layer(image, event, meta)
        elif meta.mode == "explorer":
            if meta.translate_explorer:
                self._add_frame_to_explorer_translate_layer(image, event, meta)
            else:
                self._add_frame_to_explorer_layer(image, event, meta)

    def _on_mda_finished(self, sequence: MDASequence) -> None:
        # Save layer and add increment to save name.
        if (meta := sequence.metadata.get(SEQUENCE_META_KEY)) is not None:
            save_sequence(sequence, self.viewer.layers, meta)

    def _create_empty_image_layer(
        self,
        arr: zarr.Array,
        name: str,
        sequence: MDASequence,
        **kwargs: Any,  # extra kwargs to add to layer metadata
    ) -> napari.layers.Image:
        """Create new napari layer for zarr array about to be acquired.

        Parameters
        ----------
        arr : zarr.Array
            The array to create a layer for.
        name : str
            The name of the layer.
        sequence : MDASequence
            The sequence that will be acquired.
        **kwargs
            Extra kwargs will be added to `layer.metadata`.
        """
        # we won't have reached this point if meta is None
        meta = cast(SequenceMeta, sequence.metadata.get(SEQUENCE_META_KEY))

        # add Z to layer scale
        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            scale = [1.0] * (arr.ndim - 2) + [pix_size] * 2
            if (index := sequence.used_axes.find("z")) > -1:
                if meta.split_channels and sequence.used_axes.find("c") < index:
                    index -= 1
                scale[index] = getattr(sequence.z_plan, "step", 1)

        return self.viewer.add_image(
            arr,
            name=name,
            blending="additive",
            visible=False,
            scale=scale,
            metadata={
                "mode": meta.mode,
                "useq_sequence": sequence,
                "uid": sequence.uid,
                **kwargs,
            },
        )

    def _get_defaultdict_layers(self, event: ActiveMDAEvent) -> defaultdict[Any, set]:
        layergroups = defaultdict(set)
        for lay in self.viewer.layers:
            if lay.metadata.get("uid") == event.sequence.uid:
                key = lay.metadata.get("grid")[:8]
                layergroups[key].add(lay)
        return layergroups

    def _add_frame_to_mda_layer(
        self, image: np.ndarray, event: ActiveMDAEvent, meta: SequenceMeta
    ) -> None:
        """Method called on every frame in `mda` mode."""
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

        z_arr = self._tmp_arrays[str(event.sequence.uid) + channel][0]
        z_arr[im_idx] = image

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

    def _add_frame_to_explorer_layer(
        self, image: np.ndarray, event: ActiveMDAEvent, meta: SequenceMeta
    ) -> None:

        im_idx = tuple(event.index[k] for k in event.sequence.used_axes)
        z_arr = self._tmp_arrays[str(event.sequence.uid)][0]
        z_arr[im_idx] = image

        cs = list(self.viewer.dims.current_step)
        for a, v in enumerate(im_idx):
            cs[a] = v
        self.viewer.dims.current_step = tuple(cs)

        fname = meta.file_name if meta.should_save else "Exp"
        layer = self.viewer.layers[f"{fname}_{event.sequence.uid}"]
        if not layer.visible:
            layer.visible = True
        layer.reset_contrast_limits()

    def _add_frame_to_explorer_translate_layer(
        self, image: np.ndarray, event: ActiveMDAEvent, meta: SequenceMeta
    ) -> None:
        im_idx = tuple(event.index[k] for k in event.sequence.used_axes if k != "p")
        layer_name = f"{event.pos_name}_{event.sequence.uid}"
        z_arr = self._tmp_arrays[layer_name][0]
        z_arr[im_idx] = image

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


def _determine_sequence_layers(
    sequence: MDASequence,
) -> tuple[list[str], list[tuple[str, list[int], dict[str, Any]]]]:
    """Return (axis_labels, (id, shape, and metadata)) for each layer to add for seq.

    This function is called at the beginning of a new MDA sequence to determine
    how many layers we're going to create, and what their shapes and metadata
    should be.  The data is used to create new empty zarr arrays and napari layers.

    Parameters
    ----------
    sequence : MDASequence
        The sequence to get layers for.
    img_shape : tuple[int, int]
        The YX shape of a single image in the sequence.
        (this argument might not need to be passed here, perhaps could be handled
        be the caller of this function)

    Returns
    -------
    tuple[list[str], list[tuple[str, list[int], dict[str, Any]]]]
        A 2-tuple of `(axis_labels, layer_info)` where:
            - `axis_labels` is a list of axis names, like: `['t', 'c', 'z', 'y', 'x']`
            - `layer_info` is a list of `(id, layer_shape, layer_meta)` tuples, where
              `id` is a unique id for the layer, `layer_shape` is the shape of the
              layer, and `layer_meta` is metadata to add to `layer.metadata`.  e.g.:
              `[('3670fc63-c570-4920-949f-16601143f2e3', [4, 2, 4], {})]`
    """
    # sourcery skip: extract-duplicate-method

    # if we got to this point, sequence.metadata[SEQUENCE_META_KEY] should exist
    meta = cast(SequenceMeta, sequence.metadata.get(SEQUENCE_META_KEY))

    axis_labels = list(sequence.used_axes)
    layer_shape = [sequence.sizes[k] for k in axis_labels]

    # these are all the layers we're going to create
    # each item is a tuple of (id, shape, layer_metadata)
    _layer_info: list[tuple[str, list[int], dict[str, Any]]] = []

    # in explorer/translate mode, we need to create a layer for each position
    if meta.mode == "explorer" and meta.translate_explorer:
        p_idx = axis_labels.index("p")
        axis_labels.pop(p_idx)
        layer_shape.pop(p_idx)
        for p in sequence.stage_positions:
            # TODO: modify id_ to try and divide the grids when saving
            # see also line 378 (layer.metadata["grid"])
            if not p.name or "_" not in p.name:
                raise ValueError(
                    f"Invalid stage position name: {p.name!r}. "
                    "Expected something like 'Grid_001_Pos000'"
                )
            # FIXME: the location of a stage position within a grid should not
            # be stored in the position name, but rather in the metadata.
            # e.g. sequence.metata["grid"] = {(x,y,z): (grid, grid_pos)}
            *_, grid, grid_pos = p.name.split("_")
            id_ = f"{p.name}_{sequence.uid}"
            _layer_info.append((id_, layer_shape, {"grid": grid, "grid_pos": grid_pos}))

    # in split channels mode, we need to create a layer for each channel
    elif meta.split_channels:
        c_idx = axis_labels.index("c")
        axis_labels.pop(c_idx)
        layer_shape.pop(c_idx)
        for i, ch in enumerate(sequence.channels):
            channel_id = f"{ch.config}_{i:03d}"
            id_ = f"{sequence.uid}_{channel_id}"
            _layer_info.append((id_, layer_shape, {"ch_id": channel_id}))

    # otherwise, we just need one layer
    else:
        _layer_info.append((str(sequence.uid), layer_shape, {}))

    axis_labels += ["y", "x"]
    return axis_labels, _layer_info

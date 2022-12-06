from __future__ import annotations

import contextlib
import tempfile
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Iterator, cast

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

        img_shape = (self._mmc.getImageHeight(), self._mmc.getImageWidth())
        axis_labels, layers_to_create = _determine_sequence_layers(sequence, img_shape)
        for (id_, shape, kwargs) in layers_to_create:
            tmp = tempfile.TemporaryDirectory()

            dtype = f"uint{self._mmc.getImageBitDepth()}"
            z = zarr.open(str(tmp.name), shape=shape, dtype=dtype)
            self._tmp_arrays[id_] = (z, tmp)
            self._add_image(z, id_, sequence, **kwargs)

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
        meta: SequenceMeta | None = event.sequence.metadata.get(SEQUENCE_META_KEY)
        if meta is None:
            return

        if meta.mode in ("mda", ""):
            self._mda_acquisition(image, event, meta)
        elif meta.mode == "explorer":
            if meta.translate_explorer:
                self._explorer_acquisition_translate(image, event, meta)
            else:
                self._explorer_acquisition_stack(image, event, meta)

    def _on_mda_finished(self, sequence: MDASequence) -> None:
        # Save layer and add increment to save name.
        if (meta := sequence.metadata.get(SEQUENCE_META_KEY)) is not None:
            save_sequence(sequence, self.viewer.layers, meta)

    def _add_image(
        self,
        z: zarr.Array,
        id: str,
        sequence: MDASequence,
        **kwargs: Any,  # extra kwargs to add to layer metadata
    ) -> napari.layers.Image:
        """Add a new image to the viewer."""
        # we won't have reached this point if meta is None
        meta = cast(SequenceMeta, sequence.metadata.get(SEQUENCE_META_KEY))
        fname = meta.file_name if meta.should_save else "Exp"
        layer = self.viewer.add_image(z, name=f"{fname}_{id}", blending="additive")
        layer.visible = False

        # set layer scale
        scale = [1.0] * z.ndim
        scale[-2:] = [self._mmc.getPixelSizeUm()] * 2
        if (index := sequence.used_axes.find("z")) > -1:
            if meta.split_channels and sequence.used_axes.find("c") < index:
                index -= 1
            scale[index] = getattr(sequence.z_plan, "step", 1)
        layer.scale = scale

        # add metadata to layer
        layer.metadata["mode"] = meta.mode
        layer.metadata["useq_sequence"] = sequence
        layer.metadata["uid"] = sequence.uid
        for k, v in kwargs.items():
            layer.metadata[k] = v
        return layer

    def _get_defaultdict_layers(self, event: ActiveMDAEvent) -> defaultdict[Any, set]:
        layergroups = defaultdict(set)
        for lay in self.viewer.layers:
            if lay.metadata.get("uid") == event.sequence.uid:
                key = lay.metadata.get("grid")[:8]
                layergroups[key].add(lay)
        return layergroups

    def _mda_acquisition(
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
        breakpoint()
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

    def _explorer_acquisition_stack(
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

    def _explorer_acquisition_translate(
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



def _determine_sequence_layers(
    sequence: MDASequence, img_shape: tuple[int, int]
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
        A tuple of (axis_labels, layers) where:
            - axis_labels is a list of axis names, like: `['t', 'c', 'z', 'y', 'x']`
            - layers is a list of (id, shape, layer_meta) tuples, like:
                `[('3670fc63-c570-4920-949f-16601143f2e3', [4, 2, 4], {})]`
    """
    meta = cast(SequenceMeta, sequence.metadata.get(SEQUENCE_META_KEY))

    # _get_shape_and_labels
    # sizes is a dict of each axis size, like: `{'t': 5, 'p': 0, 'c': 3, 'z': 9}`
    # so this would make `labels, shapes = [('t', 'c', 'z'), (5, 3, 9)]`
    labels = list(sequence.used_axes)
    shape = [sequence.sizes[k] for k in labels]

    # these are all the layers we're going to create
    layers: list[tuple[str, list[int], dict[str, Any]]] = []

    if meta.mode == "explorer" and meta.translate_explorer:
        # in explorer/translate mode, we need to create a layer for each position
        labels.remove("p")
        shape = [sequence.sizes[k] for k in labels] + list(img_shape)
        for p in sequence.stage_positions:
            # TODO: modify id_ to try and divide the grids when saving
            # see also line 378 (layer.metadata["grid"])
            pos = f"{p.name}_"
            id_ = pos + str(sequence.uid)
            ps = pos.split("_")
            layers.append((id_, shape, {"grid": ps[-3], "grid_pos": ps[-2]}))

    elif meta.split_channels:
        # in split channels mode, we need to create a layer for each channel
        labels.remove("c")
        shape = [sequence.sizes[k] for k in labels] + list(img_shape)
        for i, ch in enumerate(sequence.channels):
            channel_id = f"{ch.config}_{i:03d}"
            id_ = str(sequence.uid) + channel_id
            layers.append((id_, shape, {"ch_id": channel_id}))
    else:
        # otherwise, we just need one layer
        layers.append((str(sequence.uid), shape, {}))

    labels += ["y", "x"]
    print(labels, layers)    
    return labels, layers

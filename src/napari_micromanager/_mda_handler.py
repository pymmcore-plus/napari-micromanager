from __future__ import annotations

import contextlib
import tempfile
import time
from collections import deque
from typing import TYPE_CHECKING, Any, Callable, Generator, cast

import napari
import zarr
from superqt.utils import create_worker, ensure_main_thread

from ._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from ._saving import save_sequence

if TYPE_CHECKING:
    from uuid import UUID

    import napari.viewer
    import numpy as np
    from napari.layers import Image
    from pymmcore_plus import CMMCorePlus
    from pymmcore_plus.core.events._protocol import PSignalInstance
    from typing_extensions import NotRequired, TypedDict
    from useq import MDAEvent, MDASequence

    class SequenceMetaDict(TypedDict):
        """Dict containing the SequenceMeta object that we add when starting MDAs."""

        napari_mm_sequence_meta: SequenceMeta

    class ActiveMDASequence(MDASequence):
        """MDASequence that whose metadata dict contains our special SequenceMeta."""

        metadata: SequenceMetaDict  # type: ignore [assignment]

    class ActiveMDAEvent(MDAEvent):
        """Event that has been assigned a sequence."""

        sequence: ActiveMDASequence

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


# NOTE: import from pymmcore-plus when new version will be released:
# from pymmcore_plus.mda.handlers._util import get_full_sequence_axes
def get_full_sequence_axes(sequence: MDASequence) -> tuple[str, ...]:
    """Get the combined axes from sequence and sub-sequences."""
    # axes main sequence
    main_seq_axes = list(sequence.used_axes)
    if not sequence.stage_positions:
        return tuple(main_seq_axes)
    # axes from sub sequences
    sub_seq_axes: list = []
    for p in sequence.stage_positions:
        if p.sequence is not None:
            sub_seq_axes.extend(
                [ax for ax in p.sequence.used_axes if ax not in main_seq_axes]
            )
    return tuple(main_seq_axes + sub_seq_axes)


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
        self._deck: deque[tuple[np.ndarray, MDAEvent]] = deque()

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
            # TODO: should we still handle this with some sane defaults?
            return
        sequence = cast("ActiveMDASequence", sequence)

        # pause acquisition until zarr layer(s) are added
        self._mmc.mda.toggle_pause()

        # determine the new layers that need to be created for this experiment
        # (based on the sequence mode, and whether we're splitting C/P, etc.)
        axis_labels, layers_to_create = _determine_sequence_layers(sequence)

        yx_shape = [self._mmc.getImageHeight(), self._mmc.getImageWidth()]

        # now create a zarr array in a temporary directory for each layer
        for id_, shape, kwargs in layers_to_create:
            tmp = tempfile.TemporaryDirectory()
            dtype = f"uint{self._mmc.getImageBitDepth()}"
            # create the zarr array and add it to the viewer
            z = zarr.open(
                str(tmp.name),
                shape=shape + yx_shape,
                dtype=dtype,
                chunks=tuple([1] * len(shape) + yx_shape),  # VERY IMPORTANT FOR SPEED!
            )
            fname = meta.file_name if meta.should_save else "Exp"
            self._create_empty_image_layer(z, f"{fname}_{id_}", sequence, **kwargs)

            # store the zarr array and temporary directory for later cleanup
            self._tmp_arrays[id_] = (z, tmp)

        # set axis_labels after adding the images to ensure that the dims exist
        self.viewer.dims.axis_labels = axis_labels

        # init index will always be less than any event index
        self._largest_idx: tuple[int, ...] = (-1,)

        self._deck = deque()
        self._mda_running = True
        self._io_t = create_worker(
            self._watch_mda,
            _start_thread=True,
            _connect={"yielded": self._update_viewer_dims}
            # NOTE: once we have a proper writer, we can add here:
            # "finished": self._process_remaining_frames
        )

        # Set the viewer slider on the first layer frame
        self._reset_viewer_dims()

        # resume acquisition after zarr layer(s) is(are) added
        self._mmc.mda.toggle_pause()

    def _watch_mda(
        self,
    ) -> Generator[tuple[str | None, tuple[int, ...] | None], None, None]:
        """Watch the MDA for new frames and process them as they come in."""
        while self._mda_running:
            if self._deck:
                layer_name, im_idx = self._process_frame(*self._deck.pop())
                yield layer_name, im_idx
            else:
                time.sleep(0.1)

    def _on_mda_frame(self, image: np.ndarray, event: MDAEvent) -> None:
        """Called on the `frameReady` event from the core."""  # noqa: D401
        self._deck.append((image, event))

    def _process_frame(
        self, image: np.ndarray, event: MDAEvent
    ) -> tuple[str | None, tuple[int, ...] | None]:
        seq_meta = getattr(event.sequence, "metadata", None)

        if not (seq_meta and seq_meta.get(SEQUENCE_META_KEY)):
            # this is not an MDA we started
            return None, None

        event = cast("ActiveMDAEvent", event)

        # get info about the layer we need to update
        _id, im_idx, layer_name = _id_idx_layer(event)

        # update the zarr array backing the layer
        self._tmp_arrays[_id][0][im_idx] = image

        # move the viewer step to the most recently added image
        if im_idx > self._largest_idx:
            self._largest_idx = im_idx
            return layer_name, im_idx

        return None, None

    @ensure_main_thread  # type: ignore [misc]
    def _update_viewer_dims(
        self, args: tuple[str | None, tuple[int, ...] | None]
    ) -> None:
        """Update the viewer dims to match the current image."""
        layer_name, im_idx = args

        if layer_name is None or im_idx is None:
            return

        layer: Image = self.viewer.layers[layer_name]
        if not layer.visible:
            layer.visible = True

        cs = list(self.viewer.dims.current_step)
        for a, v in enumerate(im_idx):
            cs[a] = v
        self.viewer.dims.current_step = cs

    @ensure_main_thread  # type: ignore [misc]
    def _reset_viewer_dims(self) -> None:
        """Reset the viewer dims to the first image."""
        self.viewer.dims.current_step = [0] * len(self.viewer.dims.current_step)

    def _on_mda_finished(self, sequence: MDASequence) -> None:
        self._mda_running = False

        # NOTE: this will be REMOVED when using proper WRITER (e.g.
        # https://github.com/pymmcore-plus/pymmcore-MDA-writers or
        # https://github.com/fdrgsp/pymmcore-MDA-writers/tree/update_writer). See the
        # comment in _process_remaining_frames for more details.
        self._process_remaining_frames(sequence)

    def _process_remaining_frames(self, sequence: MDASequence) -> None:
        """Process any remaining frames after the MDA has finished."""
        # NOTE: when switching to a proper wtiter to save files, this method will not
        # have the sequence argument, it will not be called by `_on_mda_finished` but we
        # can link it to the self._io_t.finished signal ("finished": self._process_
        # remaining_frames) and the saving code below will be removed.
        self._reset_viewer_dims()
        while self._deck:
            self._process_frame(*self._deck.pop())

        # to remove when using proper writer
        if (meta := sequence.metadata.get(SEQUENCE_META_KEY)) is not None:
            sequence = cast("ActiveMDASequence", sequence)
            save_sequence(sequence, self.viewer.layers, meta)

    def _create_empty_image_layer(
        self,
        arr: zarr.Array,
        name: str,
        sequence: MDASequence,
        **kwargs: Any,  # extra kwargs to add to layer metadata
    ) -> Image:
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
        meta = cast("SequenceMeta", sequence.metadata.get(SEQUENCE_META_KEY))

        # add Z to layer scale
        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            scale = [1.0] * (arr.ndim - 2) + [pix_size] * 2
            if (index := sequence.used_axes.find("z")) > -1:
                if meta.split_channels and sequence.used_axes.find("c") < index:
                    index -= 1
                scale[index] = getattr(sequence.z_plan, "step", 1)
        else:
            # return to default
            scale = [1.0, 1.0]

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


def _has_sub_sequences(sequence: MDASequence) -> bool:
    """Return True if any stage positions have a sub sequence."""
    return any(p.sequence is not None for p in sequence.stage_positions)


def _determine_sequence_layers(
    sequence: ActiveMDASequence,
) -> tuple[list[str], list[tuple[str, list[int], dict[str, Any]]]]:
    # sourcery skip: extract-duplicate-method
    """Return (axis_labels, (id, shape, and metadata)) for each layer to add for seq.

    This function is called at the beginning of a new MDA sequence to determine
    how many layers we're going to create, and what their shapes and metadata
    should be. The data is used to create new empty zarr arrays and napari layers.

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
            - `axis_labels` is a list of axis names.
            e.g. `['t', 'c', 'g', 'z', 'y', 'x']`
            - `layer_info` is a list of `(id, layer_shape, layer_meta)` tuples, where
              `id` is a unique id for the layer, `layer_shape` is the shape of the
              layer, and `layer_meta` is metadata to add to `layer.metadata`. e.g.:
              `[('3670fc63-c570-4920-949f-16601143f2e3', [4, 2, 4], {})]`
    """
    # if we got to this point, sequence.metadata[SEQUENCE_META_KEY] should exist
    meta = sequence.metadata["napari_mm_sequence_meta"]

    # these are all the layers we're going to create
    # each item is a tuple of (id, shape, layer_metadata)
    _layer_info: list[tuple[str, list[int], dict[str, Any]]] = []

    axis_labels = list(get_full_sequence_axes(sequence))
    layer_shape = [sequence.sizes.get(k) or 1 for k in axis_labels]

    if _has_sub_sequences(sequence):
        for p in sequence.stage_positions:
            if not p.sequence:
                continue

            # update the layer shape for the c, g, z and t axis depending on the shape
            # of the sub sequence (sub-sequence can only have c, g, z and t).
            for key in "cgzt":
                with contextlib.suppress(KeyError, ValueError):
                    pos_shape = p.sequence.sizes[key]
                    index = axis_labels.index(key)
                    layer_shape[index] = max(layer_shape[index], pos_shape)

    # in split channels mode, we need to create a layer for each channel
    if meta.split_channels:
        c_idx = axis_labels.index("c")
        axis_labels.pop(c_idx)
        layer_shape.pop(c_idx)
        for i, ch in enumerate(sequence.channels):
            channel_id = f"{ch.config}_{i:03d}"
            id_ = f"{sequence.uid}_{channel_id}"
            _layer_info.append((id_, layer_shape, {"ch_id": channel_id}))

    else:
        _layer_info.append((str(sequence.uid), layer_shape, {}))

    axis_labels += ["y", "x"]

    return axis_labels, _layer_info


def _id_idx_layer(event: ActiveMDAEvent) -> tuple[str, tuple[int, ...], str]:
    """Get the tmp_path id, index, and layer name for a given event.

    Parameters
    ----------
    event : ActiveMDAEvent
        An event for which to retrieve the id, index, and layer name.


    Returns
    -------
    tuple[str, tuple[int, ...], str]
        A 3-tuple of (id, index, layer_name) where:
            - `id` is the id of the tmp_path for the event (to get the zarr array).
            - `index` is the index in the underlying zarr array where the event image
              should be saved.
            - `layer_name` is the name of the corresponding layer in the viewer.
    """
    meta = cast("SequenceMeta", event.sequence.metadata.get(SEQUENCE_META_KEY))

    axis_order = list(get_full_sequence_axes(event.sequence))

    suffix = ""
    prefix = meta.file_name if meta.should_save else "Exp"

    if meta.split_channels and event.channel:
        suffix = f"_{event.channel.config}_{event.index['c']:03d}"
        axis_order.remove("c")

    _id = f"{event.sequence.uid}{suffix}"

    # the index of this event in the full zarr array
    im_idx: tuple[int, ...] = ()
    for k in axis_order:
        try:
            im_idx += (event.index[k],)
        # if axis not in event.index
        # e.g. if we have both a position sequence grid and a single position
        except KeyError:
            im_idx += (0,)

    # the name of this layer in the napari viewer
    layer_name = f"{prefix}_{event.sequence.uid}{suffix}"

    return _id, im_idx, layer_name

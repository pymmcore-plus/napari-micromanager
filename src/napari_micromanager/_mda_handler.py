from __future__ import annotations

import contextlib
import tempfile
import time
from collections import deque
from typing import TYPE_CHECKING, Callable, cast

import napari
import zarr
from superqt.utils import create_worker, ensure_main_thread

from ._util import NMM_METADATA_KEY, PYMMCW_METADATA_KEY, get_full_sequence_axes

if TYPE_CHECKING:
    from collections.abc import Generator
    from uuid import UUID

    import napari.viewer
    import numpy as np
    from napari.layers import Image
    from pymmcore_plus import CMMCorePlus
    from pymmcore_plus.core.events._protocol import PSignalInstance
    from typing_extensions import TypedDict
    from useq import MDAEvent, MDASequence

    class LayerMeta(TypedDict, total=False):
        """Metadata that we add to layer.metadata."""

        useq_sequence: MDASequence
        uid: UUID
        ch_id: str


DEFAULT_NAME = "Exp"


def _get_file_name_from_metadata(sequence: MDASequence) -> str:
    """Get the file name from the MDASequence metadata."""
    meta = cast("dict", sequence.metadata.get(PYMMCW_METADATA_KEY, {}))
    return cast("str", meta.get("save_name", DEFAULT_NAME))


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
        self._mda_running: bool = False

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
        # pause acquisition until zarr layer(s) are added
        self._mmc.mda.toggle_pause()  # TODO: can we remove this somewhow?

        # determine the new layers that need to be created for this experiment
        # (based on the sequence mode, and whether we're splitting C/P, etc.)
        axis_labels, layers_to_create = _determine_sequence_layers(sequence)

        yx_shape = [self._mmc.getImageHeight(), self._mmc.getImageWidth()]
        if self._mmc.getNumberOfComponents() >= 3:
            yx_shape = [*yx_shape, 3]

        # now create a zarr array in a temporary directory for each layer
        for id_, shape, kwargs in layers_to_create:
            tmp = tempfile.TemporaryDirectory()
            dtype = f"u{self._mmc.getBytesPerPixel()}"
            # create the zarr array and add it to the viewer
            z = zarr.open(
                str(tmp.name),
                shape=shape + yx_shape,
                dtype=dtype,
                chunks=tuple([1] * len(shape) + yx_shape),  # VERY IMPORTANT FOR SPEED!
            )
            # get filename from MDASequence metadata
            fname = _get_file_name_from_metadata(sequence)
            self._create_empty_image_layer(z, f"{fname}_{id_}", sequence, kwargs)

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
            _connect={"yielded": self._update_viewer_dims},
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
        """Called on the `frameReady` event from the core."""
        self._deck.append((image, event))

    def _process_frame(
        self, image: np.ndarray, event: MDAEvent
    ) -> tuple[str | None, tuple[int, ...] | None]:
        # get info about the layer we need to update
        _id, im_idx, layer_name = _id_idx_layer(event)

        # update the zarr array backing the layer
        self._tmp_arrays[_id][0][im_idx] = image

        # move the viewer step to the most recently added image
        if im_idx > self._largest_idx:
            self._largest_idx = im_idx
            return layer_name, im_idx

        return layer_name, None

    @ensure_main_thread  # type: ignore [misc]
    def _update_viewer_dims(
        self, args: tuple[str | None, tuple[int, ...] | None]
    ) -> None:
        """Update the viewer dims to match the current image."""
        layer_name, im_idx = args

        layer: Image = self.viewer.layers[layer_name]
        if not layer.visible:
            layer.visible = True

        if im_idx is None:
            return

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
        self._reset_viewer_dims()
        while self._deck:
            self._process_frame(*self._deck.pop())

    def _create_empty_image_layer(
        self, arr: zarr.Array, name: str, sequence: MDASequence, layer_meta: LayerMeta
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
        layer_meta
            Extra info added to `layer.metadata`.
        """
        # we won't have reached this point if meta is None
        meta = sequence.metadata.get(NMM_METADATA_KEY, {})
        is_rgb = arr.shape[-1] == 3
        scale = [1.0] * (arr.ndim - (1 if is_rgb else 0))

        # add Z to layer scale
        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            scale[-2:] = [pix_size, pix_size]
            if (index := sequence.used_axes.find("z")) > -1:
                if meta.get("split_channels") and sequence.used_axes.find("c") < index:
                    index -= 1
                scale[index] = getattr(sequence.z_plan, "step", 1)

        layer_meta["useq_sequence"] = sequence
        layer_meta["uid"] = sequence.uid

        return self.viewer.add_image(
            arr,
            name=name,
            blending="opaque",
            visible=False,
            scale=scale,
            metadata={NMM_METADATA_KEY: layer_meta},
        )


def _has_sub_sequences(sequence: MDASequence) -> bool:
    """Return True if any stage positions have a sub sequence."""
    return any(p.sequence is not None for p in sequence.stage_positions)


def _determine_sequence_layers(
    sequence: MDASequence,
) -> tuple[list[str], list[tuple[str, list[int], LayerMeta]]]:
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
    tuple[list[str], list[tuple[str, list[int], LayerMeta]]]
        A 2-tuple of `(axis_labels, layer_info)` where:
            - `axis_labels` is a list of axis names.
            e.g. `['t', 'c', 'g', 'z', 'y', 'x']`
            - `layer_info` is a list of `(id, layer_shape, layer_meta)` tuples, where
              `id` is a unique id for the layer, `layer_shape` is the shape of the
              layer, and `layer_meta` is metadata to add to `layer.metadata`. e.g.:
              `[('3670fc63-c570-4920-949f-16601143f2e3', [4, 2, 4], {})]`
    """
    meta = cast("dict", sequence.metadata.get(NMM_METADATA_KEY, {}))

    # these are all the layers we're going to create
    # each item is a tuple of (id, shape, layer_metadata)
    _layer_info: list[tuple[str, list[int], LayerMeta]] = []

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
    if meta.get("split_channels", False):
        c_idx = axis_labels.index("c")
        axis_labels.pop(c_idx)
        layer_shape.pop(c_idx)
        for i, ch in enumerate(sequence.channels):
            channel_id = f"{ch.config}_{i:03d}"
            id_ = f"{channel_id}_{sequence.uid}"
            _layer_info.append((id_, layer_shape, {"ch_id": channel_id}))

    else:
        _layer_info.append((str(sequence.uid), layer_shape, {}))

    axis_labels += ["y", "x"]

    return axis_labels, _layer_info


def _id_idx_layer(event: MDAEvent) -> tuple[str, tuple[int, ...], str]:
    """Get the tmp_path id, index, and layer name for a given event.

    Parameters
    ----------
    event : MDAEvent
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
    seq = cast("MDASequence", event.sequence)
    meta = cast("dict", seq.metadata.get(NMM_METADATA_KEY, {}))
    axis_order = list(get_full_sequence_axes(seq))

    ch_id = ""
    # get filename from MDASequence metadata
    prefix = _get_file_name_from_metadata(seq)

    if meta.get("split_channels", False) and event.channel:
        ch_id = f"{event.channel.config}_{event.index['c']:03d}_"
        axis_order.remove("c")

    _id = f"{ch_id}{seq.uid}"

    # the index of this event in the full zarr array
    im_idx: tuple[int, ...] = ()
    for k in axis_order:
        try:
            im_idx += (event.index[k],)
        # if axis not in event.index
        # e.g. if we have both a position with and one without a sub-sequence grid
        except KeyError:
            im_idx += (0,)

    # the name of this layer in the napari viewer
    layer_name = f"{prefix}_{ch_id}{seq.uid}"

    return _id, im_idx, layer_name

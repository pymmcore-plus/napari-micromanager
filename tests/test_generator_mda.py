from __future__ import annotations

from typing import TYPE_CHECKING

from useq import MDAEvent

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytestqt.qtbot import QtBot

    from napari_micromanager.main_window import MainWindow


def test_generator_mda_does_not_crash(main_window: MainWindow, qtbot: QtBot) -> None:
    """Running an MDA from a generator should not crash the handler."""

    def _events() -> Iterator[MDAEvent]:
        yield MDAEvent(exposure=5)
        yield MDAEvent(exposure=5)

    mmc = main_window._mmc
    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=5000):
        mmc.run_mda(_events())

    # No zarr-backed MDA layers should have been created.
    layer_names = [layer.name for layer in main_window.viewer.layers]
    assert all("Exp_" not in n for n in layer_names)

    # The acquired frames should still be visible in the preview layer.
    assert "preview" in layer_names
    assert main_window.viewer.layers["preview"].data.shape == (512, 512)

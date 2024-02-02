"""Run napari-micromanager as a script with ``python -m napari_micromanager``."""
from __future__ import annotations

import argparse
import sys
from typing import Sequence


def main(args: Sequence[str] | None = None) -> None:
    """Create a napari viewer and add the MicroManager plugin to it."""
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(description="Enter string")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="Config file to load",
        nargs="?",
    )
    parsed_args = parser.parse_args(args)

    import napari

    from napari_micromanager.main_window import MainWindow

    viewer = napari.Viewer()
    win = MainWindow(viewer, config=parsed_args.config)
    dw = viewer.window.add_dock_widget(win, name="MicroManager", area="top")
    if hasattr(dw, "_close_btn"):
        dw._close_btn = False
    napari.run()


if __name__ == "__main__":
    main()

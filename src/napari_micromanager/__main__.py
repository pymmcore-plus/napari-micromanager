"""Run napari-micromanager as a script with ``python -m napari_micromanager``."""
import argparse
import sys


def main(argv: list[str] = sys.argv) -> None:
    """Create a napari viewer and add the MicroManager plugin to it."""
    parser = argparse.ArgumentParser(description="Enter string")
    parser.add_argument(
        "config",
        type=str,
        default=None,
        help="Config file to load",
        nargs="?",
    )
    args = parser.parse_args(argv[1:])

    import napari

    from napari_micromanager.main_window import MainWindow

    viewer = napari.Viewer()
    win = MainWindow(viewer, config=args.config)
    dw = viewer.window.add_dock_widget(win, name="MicroManager", area="top")
    if hasattr(dw, "_close_btn"):
        dw._close_btn = False
    napari.run()


if __name__ == "__main__":
    main()

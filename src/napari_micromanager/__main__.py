def main() -> None:
    import napari
    from napari_micromanager.main_window import MainWindow

    viewer = napari.Viewer()
    win = MainWindow(viewer)
    dw = viewer.window.add_dock_widget(win, name="MicroManager", area="top")
    if hasattr(dw, "_close_btn"):
        dw._close_btn = False
    napari.run()


if __name__ == "__main__":
    main()

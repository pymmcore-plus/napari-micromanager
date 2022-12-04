from unittest.mock import patch

from napari_micromanager.__main__ import main


def test_cli_main() -> None:
    import napari
    from napari.qt import QtViewer

    with patch("napari.run") as mock_run:
        with patch("qtpy.QtWidgets.QMainWindow.show") as mock_show:
            main()
    mock_run.assert_called_once()
    mock_show.assert_called_once()

    # this is to prevent a leaked widget error in the NEXT test
    napari.current_viewer().close()
    QtViewer._instances.clear()

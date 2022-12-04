from unittest.mock import patch

from napari_micromanager.__main__ import main


def test_cli_main() -> None:
    with patch("napari.run") as mock_run:
        with patch("qtpy.QtWidgets.QMainWindow.show") as mock_show:
            main()
    mock_run.assert_called_once()
    mock_show.assert_called_once()

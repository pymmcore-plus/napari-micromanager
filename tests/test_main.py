from pathlib import Path
from unittest.mock import patch

import pytest
from napari_micromanager.__main__ import main
from pymmcore_plus import CMMCorePlus


@pytest.mark.parametrize(
    "argv",
    [[""], ["", str(Path(__file__).parent / "test_config.cfg")], ["", "nonexistant"]],
)
def test_cli_main(argv: list) -> None:
    import napari
    from napari.qt import QtViewer

    with patch("napari.run") as mock_run:
        with patch("qtpy.QtWidgets.QMainWindow.show") as mock_show:
            with patch("napari.utils.notifications.show_warning") as mock_warning:
                main(argv)
    mock_run.assert_called_once()
    mock_show.assert_called_once()

    if "test_config" in argv[-1]:
        assert len(CMMCorePlus.instance().getLoadedDevices()) > 1
    elif "nonexistant" in argv[-1]:
        mock_warning.assert_called_once()

    # this is to prevent a leaked widget error in the NEXT test
    napari.current_viewer().close()
    QtViewer._instances.clear()

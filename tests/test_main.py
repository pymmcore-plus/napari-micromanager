from pathlib import Path
from unittest.mock import patch

import pytest
from napari_micromanager.__main__ import main
from napari_micromanager._util import USER_CONFIGS_PATHS
from pymmcore_plus import CMMCorePlus


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--config", str(Path(__file__).parent / "test_config.cfg")],
        ["-c", "nonexistent"],
    ],
)
def test_cli_main(argv: list) -> None:
    import napari
    from napari.qt import QtViewer

    with patch("napari.run") as mock_run:
        with patch("qtpy.QtWidgets.QMainWindow.show") as mock_show:
            if "nonexistent" in argv:
                with pytest.warns():
                    main(argv)
            else:
                main(argv)

    mock_run.assert_called_once()
    mock_show.assert_called_once()

    if argv and "test_config" in argv[-1]:
        assert len(CMMCorePlus.instance().getLoadedDevices()) > 1

    # this is to prevent a leaked widget error in the NEXT test
    napari.current_viewer().close()
    QtViewer._instances.clear()

    if USER_CONFIGS_PATHS.exists():
        USER_CONFIGS_PATHS.unlink()

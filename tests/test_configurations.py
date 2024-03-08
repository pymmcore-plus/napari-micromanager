import json
from pathlib import Path

import pytest
from napari_micromanager._init_system_configs import (
    InitializeSystemConfigurations,
)
from napari_micromanager._util import USER_CONFIGS_PATHS
from pymmcore_plus import CMMCorePlus
from pytestqt.qtbot import QtBot

DEMO = "MMConfig_demo.cfg"


configs = [None, Path(__file__).parent / "test_config.cfg"]


@pytest.mark.parametrize("config", configs)
def test_config_init(qtbot: QtBot, core: CMMCorePlus, config: Path | None):
    init = InitializeSystemConfigurations(mmcore=core, config=config)

    with open(USER_CONFIGS_PATHS) as f:
        data = json.load(f)
        # the default config should be in the json file
        assert DEMO in [Path(path).name for path in data["paths"]]

        if config is None:
            assert len(data["paths"]) == 1
            assert init._startup_dialog.isVisible()
            combo = init._startup_dialog.cfg_combo
            current_cfg = combo.currentText()
            assert Path(current_cfg).name == DEMO
            assert [Path(combo.itemText(i)).name for i in range(combo.count())] == [
                DEMO,
                "New Hardware Configuration",
            ]
            # simulate click on ok
            init._startup_dialog.accept()

        else:
            assert len(data["paths"]) == 2
            assert not hasattr(init, "_startup_dialog")
            current_cfg = config
            assert str(current_cfg) in data["paths"]

        assert core.systemConfigurationFile() == str(current_cfg)

    USER_CONFIGS_PATHS.unlink()

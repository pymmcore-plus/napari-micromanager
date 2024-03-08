from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from napari_micromanager._init_system_configs import (
    InitializeSystemConfigurations,
)
from napari_micromanager._util import USER_CONFIGS_PATHS

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot

DEMO = "MMConfig_demo.cfg"
NEW = "New Hardware Configuration"

configs = [None, Path(__file__).parent / "test_config.cfg"]


@pytest.mark.parametrize("config", configs)
@pytest.mark.parametrize("wiz", [True, False])
def test_config_init(qtbot: QtBot, core: CMMCorePlus, config: Path | None, wiz: bool):
    assert not USER_CONFIGS_PATHS.exists()

    init = InitializeSystemConfigurations(mmcore=core, config=config)

    with open(USER_CONFIGS_PATHS) as f:
        data = json.load(f)
        # the default config should be in the json file
        assert DEMO in [Path(path).name for path in data["paths"]]

        if config is None:
            assert init._startup_dialog.isVisible()
            combo = init._startup_dialog.cfg_combo
            current_cfg = combo.currentText()
            assert Path(current_cfg).name == DEMO
            assert DEMO and NEW in [
                Path(combo.itemText(i)).name for i in range(combo.count())
            ]

            # set the combo to new so that after accepting the config wizard should
            # be visible
            combo.setCurrentText(NEW if wiz else DEMO)

            # simulate click on ok
            init._startup_dialog.accept()

            # only if DEMO cfg was selected, the config wizard should be visible
            if wiz:
                assert init._startup_dialog._cfg_wizard.isVisible()

        else:
            assert not hasattr(init, "_startup_dialog")
            current_cfg = config
            assert str(current_cfg) in data["paths"]

        # a config should have been loaded only if DEMO cfg was selected
        if not wiz:
            assert core.systemConfigurationFile() == str(current_cfg)

    USER_CONFIGS_PATHS.unlink()


# TODO: test the config wizard and the menu actions

from pathlib import Path

from micromanager_gui.prop_browser import PropBrowser


def test_prop_browser(qtbot):
    from pymmcore_plus import CMMCorePlus

    mmcore = CMMCorePlus()
    cfg = Path(__file__).parent / "test_config.cfg"
    mmcore.loadSystemConfiguration(str(cfg))
    pb = PropBrowser(mmcore)
    qtbot.addWidget(pb)
    pb.show()

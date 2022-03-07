from pymmcore_plus import CMMCorePlus

from micromanager_gui._core_widgets import PropertyBrowser


def test_prop_browser(global_mmcore, qtbot):
    pb = PropertyBrowser(mmcore=global_mmcore)
    qtbot.addWidget(pb)
    pb.show()


def test_prop_browser_core_reset(global_mmcore: CMMCorePlus, qtbot):
    pb = PropertyBrowser(mmcore=global_mmcore)
    qtbot.addWidget(pb)
    global_mmcore.loadSystemConfiguration()

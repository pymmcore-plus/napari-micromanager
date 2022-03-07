from micromanager_gui._core_widgets import PropertyBrowser


def test_prop_browser(global_mmcore, qtbot):
    pb = PropertyBrowser(mmcore=global_mmcore)
    qtbot.addWidget(pb)
    pb.show()

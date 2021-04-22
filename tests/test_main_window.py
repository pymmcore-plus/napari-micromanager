import pytest
from micromanager_gui.qmmcore import mmcore

# tests are critical if you want to be able to build on things
# without breaking previous functionality.  Keep tests as small
# as possible.  Many tiny tests are much better than few big ones.


# a pytest fixture is an object that you can setup in one function
# and then reuse all of your tests.  By default it will be setup
# fresh for each test.  You "use" a fixture simply by putting the
# *name* of the fixture function as a parameter to one of your tests
# https://docs.pytest.org/en/stable/fixture.html
@pytest.fixture
def main_window(qtbot):
    # qtbot is, itself, a fixture provided by pytest-qt
    # that starts a QApp for us
    from micromanager_gui.main_window import MainWindow

    win = MainWindow(viewer=None)
    win.load_cfg()
    return win


# all tests must start with the prefix `test_`
# here, we use the `main_window` fixture defined above.
def test_load_default_config(main_window):
    """Test that load_cfg loads the default config."""

    # the main idea in a test is to "assert" things you expect
    # to be true. Here we assert the demo_config (which was loaded
    # in the main_window fixture. will load these devices:
    expected = {
        "DHub",
        mmcore.getCameraDevice().result(),
        "Objective",
        mmcore.getFocusDevice().result(),
        mmcore.getXYStageDevice().result(),
        "Core",
    }
    assert expected.issubset(set(mmcore.getLoadedDevices().result()))


def test_stage_xy_position(main_window):
    """Test that we can move the stage."""
    x, y = mmcore.getXPosition().result(), mmcore.getYPosition().result()
    assert (x, y) == (0, 0)

    xystep = main_window.xy_step_size_SpinBox.value()

    main_window.stage_x_left()
    x, y = int(mmcore.getXPosition().result()), mmcore.getYPosition().result()
    assert (x, y) == (-xystep, 0)

    main_window.stage_x_right()
    x, y = int(mmcore.getXPosition().result()), mmcore.getYPosition().result()
    assert (x, y) == (0, 0)

    main_window.stage_y_up()
    x, y = mmcore.getXPosition().result(), int(mmcore.getYPosition().result())
    assert (x, y) == (0, xystep)

    main_window.stage_y_down()
    x, y = mmcore.getXPosition().result(), int(mmcore.getYPosition().result())
    assert (x, y) == (0, 0)


def test_stage_z_position(main_window):
    zpos = mmcore.getPosition(mmcore.getFocusDevice().result()).result()
    assert zpos == 0

    main_window.stage_z_up()
    expected = main_window.z_step_size_doubleSpinBox.value()
    assert mmcore.getPosition(mmcore.getFocusDevice().result()).result() == expected

    main_window.stage_z_down()
    assert mmcore.getPosition(mmcore.getFocusDevice().result()).result() == 0

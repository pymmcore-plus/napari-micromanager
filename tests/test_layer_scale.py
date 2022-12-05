from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from napari_micromanager._gui_objects._mda_widget import MultiDWidget
from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from napari_micromanager.main_window import MainWindow
from pymmcore_widgets._zstack_widget import ZRangeAroundSelect

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.mark.parametrize("Z", ["", "withZ"])
@pytest.mark.parametrize("splitC", ["", "splitC"])
@pytest.mark.parametrize("C", ["", "withC"])
@pytest.mark.parametrize("T", ["", "withT"])
def test_layer_scale(qtbot: QtBot, main_window: MainWindow, T, C, splitC, Z):

    Z_RANGE = 5
    STEP_SIZE = 2
    mmc = main_window._mmc
    mmc.setProperty("Objective", "Label", "Nikon 20X Plan Fluor ELWD")
    main_window._show_dock_widget("MDA")
    _mda = main_window._dock_widgets["MDA"].widget()
    assert isinstance(_mda, MultiDWidget)

    _mda.time_groupbox.setChecked(bool(T))
    _mda.time_groupbox.time_comboBox.setCurrentText("ms")
    _mda.time_groupbox.timepoints_spinBox.setValue(3)
    _mda.time_groupbox.interval_spinBox.setValue(250)

    _mda.stack_groupbox.setChecked(bool(Z))
    _mda.stack_groupbox._zmode_tabs.setCurrentIndex(1)
    z_range_wdg = _mda.stack_groupbox._zmode_tabs.widget(1)
    assert isinstance(z_range_wdg, ZRangeAroundSelect)

    z_range_wdg._zrange_spinbox.setValue(Z_RANGE)
    _mda.stack_groupbox._zstep_spinbox.setValue(STEP_SIZE)

    # 2 Channels
    _mda.channel_groupbox.add_ch_button.click()
    _mda.channel_groupbox.channel_tableWidget.cellWidget(0, 1).setValue(5)
    if C:
        _mda.channel_groupbox.add_ch_button.click()
        _mda.channel_groupbox.channel_tableWidget.cellWidget(1, 1).setValue(5)
    if C and splitC:
        _mda.checkBox_split_channels.setChecked(True)

    mmc = main_window._mmc
    mda = _mda.get_state()
    mda.metadata[SEQUENCE_META_KEY] = SequenceMeta(
        mode="mda", split_channels=_mda.checkBox_split_channels.isChecked()
    )

    main_window._on_mda_started(mda)

    layer = main_window.viewer.layers[-1]
    # if mda.z_plan, z stack will have 4 images
    if len(mda.z_plan) == 4:
        data_shape = layer.data.shape
        assert layer.scale[data_shape.index(4)] == float(STEP_SIZE)
    else:
        for idx, val in enumerate(reversed(layer.scale)):
            if idx <= 1:
                assert val == mmc.getPixelSizeUm()
            else:
                assert val == 1.0

# # to create a new CMMCorePlus() for every test
# @pytest.fixture
# def core(monkeypatch):
#     new_core = CMMCorePlus()
#     monkeypatch.setattr("pymmcore_plus.core._mmcore_plus._instance", new_core)
#     return new_core


# @pytest.fixture
# def main_window(core: CMMCorePlus, make_napari_viewer):
#     viewer = make_napari_viewer()
#     win = MainWindow(viewer=viewer)
#     assert core == win._mmc
#     config_path = str(Path(__file__).parent / "test_config.cfg")
#     win._mmc.loadSystemConfiguration(config_path)
#     return win


# @pytest.fixture
# def explorer_two_channels(main_window: MainWindow) -> ExplorerTuple:

#     explorer = main_window.explorer
#     explorer.scan_size_spinBox_r.setValue(2)
#     explorer.scan_size_spinBox_c.setValue(2)
#     explorer.ovelap_spinBox.setValue(0)
#     explorer.add_ch_explorer_Button.click()
#     explorer.channel_explorer_comboBox.setCurrentText("Cy5")
#     explorer.add_ch_explorer_Button.click()
#     explorer.channel_explorer_comboBox.setCurrentText("FITC")

#     # set grids position
#     explorer.stage_pos_groupBox.setChecked(True)
#     pos_table = explorer.stage_tableWidget

#     grids = [("Grid_001", 0.0, 0.0, 0.0), ("Grid_002", 0.0, 0.0, 0.0)]
#     for idx, i in enumerate(grids):
#         idx = pos_table.rowCount()
#         pos_table.insertRow(idx)
#         name = QTableWidgetItem(i[0])
#         pos_table.setItem(idx, 0, name)
#         x = QTableWidgetItem(str(i[1]))
#         pos_table.setItem(idx, 1, x)
#         y = QTableWidgetItem(str(i[2]))
#         pos_table.setItem(idx, 2, y)
#         z = QTableWidgetItem(str(i[3]))
#         pos_table.setItem(idx, 3, z)

#     # set z-stack
#     explorer.stack_groupBox.setChecked(True)
#     explorer.z_tabWidget.setCurrentIndex(1)
#     explorer.zrange_spinBox.setValue(2)
#     explorer.step_size_doubleSpinBox.setValue(1.0)

#     # set timelapse
#     # main_win.explorer.time_groupBox.setChecked(True)
#     # main_win.explorer.timepoints_spinBox.setValue(2)
#     # main_win.explorer.interval_spinBox.setValue(3)

#     return main_window, explorer

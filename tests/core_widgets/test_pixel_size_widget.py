from pymmcore_plus import CMMCorePlus

from micromanager_gui._core_widgets._set_pixel_size import PixelSizeWidget


def test_px_size_configurator(qtbot, global_mmcore: CMMCorePlus):
    mmc = global_mmcore

    px_size_wdg = PixelSizeWidget(mmc)
    assert ["Res10x", "Res20x", "Res40x"] == list(mmc.getAvailablePixelSizeConfigs())
    assert px_size_wdg.table.rowCount() == 3

    obj_wdg_row_3 = px_size_wdg.table.cellWidget(2, 0)
    mag_wdg_row_3 = px_size_wdg.table.cellWidget(2, 1)
    assert obj_wdg_row_3.currentText() == "Nikon 40X Plan Fluor ELWD"
    assert mag_wdg_row_3.value() == 40

    px_size_wdg.new_row_button.click()
    assert px_size_wdg.table.rowCount() == 4
    obj_wdg_row_1 = px_size_wdg.table.cellWidget(1, 0)
    assert obj_wdg_row_1.property("row") == 1

    px_size_wdg._delete_selected_row(1)
    px_size_wdg.new_row_button.click()
    rows = px_size_wdg.table.rowCount()
    obj_wdg_last_row = px_size_wdg.table.cellWidget(rows - 1, 0)
    assert obj_wdg_last_row.property("row") == 3

    mag_wdg_row_2 = px_size_wdg.table.cellWidget(2, 1)
    cam_px_size_wdg_row_2 = px_size_wdg.table.cellWidget(2, 2)
    img_px_size_wdg_row_2 = px_size_wdg.table.cellWidget(2, 3)

    mag_wdg_row_2.setValue(20)
    cam_px_size_wdg_row_2.setValue(6.5000)
    assert img_px_size_wdg_row_2.value() == 6.500 * mmc.getMagnificationFactor() / 20

    for r in range(3):
        px_size_wdg._delete_selected_row(r)
    assert px_size_wdg.table.rowCount() == 2

    obj_wdg_row_1 = px_size_wdg.table.cellWidget(0, 0)
    mag_wdg_row_1 = px_size_wdg.table.cellWidget(0, 1)
    cam_px_size_wdg_row_1 = px_size_wdg.table.cellWidget(0, 2)
    img_px_size_wdg_row_1 = px_size_wdg.table.cellWidget(0, 3)

    obj_wdg_row_1.setCurrentText("Nikon 10X S Fluor")
    assert mag_wdg_row_1.value() == 10
    cam_px_size_wdg_row_1.setValue(6.5000)
    assert img_px_size_wdg_row_1.value() == (6.500 * mmc.getMagnificationFactor() / 10)

    obj_wdg_row_2 = px_size_wdg.table.cellWidget(1, 0)
    mag_wdg_row_2 = px_size_wdg.table.cellWidget(1, 1)
    cam_px_size_wdg_row_2 = px_size_wdg.table.cellWidget(1, 2)
    img_px_size_wdg_row_2 = px_size_wdg.table.cellWidget(1, 3)

    obj_wdg_row_2.setCurrentText("Nikon 20X Plan Fluor ELWD")
    assert mag_wdg_row_2.value() == 20
    cam_px_size_wdg_row_2.setValue(6.5000)
    assert img_px_size_wdg_row_2.value() == (6.500 * mmc.getMagnificationFactor() / 20)

    assert px_size_wdg.table.rowCount() == 2

    px_size_wdg.table._set_mm_pixel_size()

    available_px_cfg = list(mmc.getAvailablePixelSizeConfigs())
    assert len(available_px_cfg) == 3

    assert ["Res40x", "px_size_10x", "px_size_20x"] == available_px_cfg

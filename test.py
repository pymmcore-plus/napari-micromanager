import numpy as np
from pathlib import Path
import sys
import os


save_folder = Path("/Users/Gaspian/Desktop/save_test/testMDA_ps0002_ts0005_zs0005_['DAPI', 'FITC', 'Cy3']")


def create_stack_array(tp, Zp, nC):
        width = 512
        height = 512
        bitd=16
        dt = f'uint{bitd}'
        mda_stack= np.empty((tp, Zp, nC, height, width), dtype=dt)
        return mda_stack


for folders in os.scandir(save_folder):
    if folders.is_dir():
        name_pos_folder = Path(folders)
        path_to_pos_folder = save_folder / name_pos_folder
        print(path_to_pos_folder)
        t_stack = create_stack_array(5,5,3)
        for timep in range (len(os.listdir(path_to_pos_folder))):
            t_stack = t_stack + os.listdir(path_to_pos_folder)[timep]
            # t_stack[timep]= os.listdir(path_to_pos_folder)[timep]







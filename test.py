import numpy as np
from pathlib import Path
import sys
import os

position = 0
timepoints = 1
n_steps = 2
nC = 3

parent_path = Path('/Users/Gaspian/Desktop/save_test')

save_folder_name = f'test_Pos{position}_t{timepoints}_z{n_steps}_c{nC}'
save_folder = parent_path / save_folder_name

if save_folder.exists():
    i = len(os.listdir(parent_path))
    save_folder = Path(f'{save_folder_name}_{i-1}')
    save_folder_1 = parent_path / save_folder
    print(save_folder)
    os.makedirs(save_folder_1)#, exist_ok=True)
else:
    os.makedirs(save_folder)




import numpy as np
from pathlib import Path
import sys
import os
from skimage import io
import matplotlib.pyplot as plt

import napari

save_folder = Path("/Users/Gaspian/Desktop/save_test")



def create_stack_array(tp, Zp, nC):
    x = 512
    y = 512
    bitd=16
    dt = f'uint{bitd}'
    mda_stack = np.empty((tp, Zp, nC, x, y), dtype=dt)
    return mda_stack

zp = 3
ch = 3
tp = 4
ps = 3

t0p0 = create_stack_array(1, zp, ch)
t0p1 = create_stack_array(1, zp, ch)
t0p2 = create_stack_array(1, zp, ch)

t1p0 = create_stack_array(1, zp, ch)
t1p1 = create_stack_array(1, zp, ch)
t1p2 = create_stack_array(1, zp, ch)

t2p0 = create_stack_array(1, zp, ch)
t2p1 = create_stack_array(1, zp, ch)
t2p2 = create_stack_array(1, zp, ch)

t3p0 = create_stack_array(1, zp, ch)
t3p1 = create_stack_array(1, zp, ch)
t3p2 = create_stack_array(1, zp, ch)


length_l = tp*ps


l = [t0p0, t0p1, t0p2, t1p0, t1p1, t1p2, t2p0, t2p1, t2p2, t3p0, t3p1, t3p2]
#l = ['t0p0', 't0p1', 't0p2', 't1p0', 't1p1', 't1p2', 't2p0', 't2p1', 't2p2', 't3p0', 't3p1', 't3p2']

print(f'ts*ps = {length_l}, len(l) = {len(l)}')





i = 0
for p in range(ps):
    st_time = []
    for _ in range(tp):
        st = l[i]
        st_time.append(st)
        i = i + ps

    stack = np.concatenate(st_time, axis=0)
    print(stack.shape)

    pth = save_folder / f'Pos_{p}.tif'
    io.imsave(str(pth), stack, imagej=True, check_contrast=False)

    i = p + 1




#make hyperstack
# iterator = 0
# for pos in range(len(self.pos_list)):
#     t_stack = self.create_stack_array(0, n_steps, nC)
#     for tp in range(timepoints):
#         ts = self.acq_stack_list[iterator]
#         t_stack = np.concatenate((t_stack, ts), axis=0)
#         iterator = iterator + len(self.pos_list)
#     #save hyperstack
#     if self.save_groupBox.isChecked():
#         pos_format = format(pos, '04d')
#         t_format = format(timepoints, '04d')
#         z_position_format = format(n_steps, '04d')
#         save_name = f'{self.fname_lineEdit.text()}_p{pos_format}_ts{t_format}_zs{z_position_format}_{self.list_ch}'
#         pth = save_folder / f'Pos_{pos_format}' / f'{save_name}.tif'
#         io.imsave(str(pth), t_stack, imagej=True, check_contrast=False)

#     iterator = pos + 1




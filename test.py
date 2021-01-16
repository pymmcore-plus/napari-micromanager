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
    t_st = create_stack_array(0, zp, ch)
    for _ in range(tp):
        #print(f'i = {i}')
        st = l[i]
        #print(f'st = {st}')
        #st_time.append(st)
        t_st = np.concatenate((t_st, st), axis=0)
        i = i + ps
        #print(f'i_new = {i}\n')
    pth = save_folder / f'Pos_{p}.tif'
    io.imsave(str(pth), t_st, imagej=True, check_contrast=False)
    i = p + 1








#print(st_time)


# t_st = create_stack_array(0, zp, ch)
# print(f't_st.shape start = {t_st.shape}')

# for i in range(len(l)):
#     st = st_time[i]
#     t_st = np.concatenate((t_st, st), axis=0)

#     print(f'    t_st.shape iteration = {t_st.shape}')

# print(f'        t_st.shape final = {t_st.shape}')









# i = 0
# stk_time = []
# for _ in range(tp):
#     print(f'i = {i}')
#     stk = l[i]
#     print(f'stk = {stk}')
#     stk_time.append(stk)
#     i = i + ps
#     print(f'i_new = {i}\n')
    
# print(stk_time)

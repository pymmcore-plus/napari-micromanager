import numpy as np
from pathlib import Path
import sys
import os
from skimage import io
import matplotlib.pyplot as plt


def create_stack_array(tp, Zp, nC):
        bitd=16
        dt = f'uint{bitd}'
        mda_stack= np.empty((tp, Zp, nC, 512, 512), dtype=dt)
        return mda_stack

# im1 = '/Users/Gaspian/Desktop/t1.tif'
# im2 = '/Users/Gaspian/Desktop/t2.tif'

# img1 = io.imread(im1)
# img2 = io.imread(im2)

# print(img1.shape)
# print(img2.shape)

s1 = create_stack_array(1 ,5, 3)
s2 = create_stack_array(1, 5, 3)
s3 = create_stack_array(1, 5, 3)

l = [s1,s2,s3]

l = tuple(l)

l = np.vstack(l)
print(l.shape)





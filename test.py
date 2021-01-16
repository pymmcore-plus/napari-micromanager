import numpy as np
from pathlib import Path
import sys
import os
from skimage import io


save_folder = Path("/Users/Gaspian/Desktop/save_test")


def name(name):
    return name

a = name('name')
print(a)


for i in range(3):
   stk = create_stack_array(tp, Zp, nC)
    





def create_stack_array(tp, Zp, nC):
    bitd=16
    dt = f'uint{bitd}'
    mda_stack = np.empty((tp, Zp, nC), dtype=dt)
    return mda_stack

# stack = create_stack_array(0, 5, 3)
# p_array = create_stack_array(1, 5, 3)
# print(stack.shape)
# print(p_array.shape)

# stk = np.concatenate((stack, p_array), axis=0) # axes are 0-indexed, i.e. 0, 1, 2
# print(stk.shape)


# stack = create_stack_array(0, 0, 5, 3)
# p_array = create_stack_array(0, 1, 5, 3)
# print(stack.shape)
# for i in range(3):
#     p_array = np.append(stack, p_array, axis=1)
#     print(p_array.shape)
# for i in range(3):
#     stack = create_stack_array(0, 1, 5, 3)
#     p_array = np.append(p_array, stack, axis=1)

# print(p_array.shape)















from typing import Tuple

import numpy as np


def get_devices_and_props(self):
    mmc = None
    # List devices and properties that you can set
    devices = mmc.getLoadedDevices()
    print("\nDevice status:__________________________")
    for i in range(len(devices)):
        device = devices[i]
        properties = mmc.getDevicePropertyNames(device)
        for p in range(len(properties)):
            prop = properties[p]
            values = mmc.getAllowedPropertyValues(device, prop)
            print(f"Device: {str(device)}  Property: {str(prop)} Value: {str(values)}")
    print("________________________________________")


def get_groups_list(self):
    mmc = None
    group = []
    for groupName in mmc.getAvailableConfigGroups():
        print(f"*********\nGroup_Name: {str(groupName)}")
        for configName in mmc.getAvailableConfigs(groupName):
            group.append(configName)
            print(f"Config_Name: {str(configName)}")
            props = str(mmc.getConfigData(groupName, configName).getVerbose())
            print(f"Properties: {props}")
        print("*********")


def extend_array_for_index(array: np.ndarray, index: Tuple[int, ...]):
    """Return `array` padded with zeros if necessary to contain `index`."""

    # if the incoming index is outside of the bounds of the current layer.data
    # pad layer.data with zeros to accomodate the incoming index
    if any(x >= y for x, y in zip(index, array.shape)):
        newshape = list(array.shape)
        for i, (x, y) in enumerate(zip(index, array.shape)):
            newshape[i] = max(x + 1, y)

        new_array = np.zeros(newshape)
        # populate with existing data
        new_array[tuple(slice(s) for s in array.shape)] = array
        return new_array

    # otherwise just return the incoming array
    return array


def check_filename(fname, list_dir):
    """
    Ckeck the input filename and modify it to add _nnn in the end.
    The get_filename(fname,list_dir) function check if the name 
    is already present in the save_path and incremant the _nnn accordingly.

    filename examples: user input -> output:
        - mda       -> mda_000
        - mda_3     -> mda_003
        - mda_0001  -> mda_001
        - mda1      -> mda_001
        - mda011021 -> mda011021_000
        - mda_011021 -> mda_011021_000

        - mda (with split positions) -> mda_000_[p000], mda_000_[p001], mda_000_[p002]
        - ...
    """
    try:
        n = fname.split('_')[-1]
        int_n = int(n)
        
        if len(n) == 3 and int_n >= 0:
            fname = get_filename(fname,list_dir)
        
        elif len(n) != 3 and len(n) <=4 and int_n >= 0:
            s = ''
            for i in fname.split('_')[:-1]:
                s = s + i + '_'
                print(s)
            print('s', s)
            fname = s + '{0:03}'.format(int_n)
            fname = get_filename(fname,list_dir)
        
        else:
            fname = fname + '_000'
            fname = get_filename(fname,list_dir)

    except ValueError:
        n = ''
        for i in range(1,len(fname)+1):
            try:
                n += str(int(fname[-i]))
            except ValueError:
                break
        if len(n) > 0 and len(n) <= 4:
            n = n[::-1]
            fname = fname.replace(n, '_' + '{0:03}'.format(int(n)))
            fname = get_filename(fname,list_dir)
        else:
            fname = fname + '_000'
            fname = get_filename(fname,list_dir)
        
    return fname
    
def get_filename(fname, list_dir):
    """
        check if the filename_nnn used to save the layer exists
        and increment _nnn accordingly.
    """

    val = int(fname.split('_')[-1])
        
    while True:
        new_val = '{0:03}'.format(val)
        fname = fname[:-3] + new_val
        if not any(fname in f for f in list_dir):
            break
        else:
            val += 1
    return fname
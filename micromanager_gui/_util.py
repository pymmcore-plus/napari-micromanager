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

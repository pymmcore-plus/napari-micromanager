from pymmcore_plus import CMMCorePlus, RemoteMMCore


class AutofocusDevice:
    def __init__(self, mmcore: CMMCorePlus or RemoteMMCore):
        super().__init__()
        self._mmc = mmcore

    @classmethod
    def set(self, key, mmcore):
        if key == "TIPFSStatus":  # key = mmcore.getAutoFocusDevice() -> "TIPFStatus"
            return NikonPFS(mmcore)

    def isEngaged(self) -> bool:
        return self._mmc.isContinuousFocusEnabled()

    def isLocked(self) -> bool:
        return self._mmc.isContinuousFocusLocked()

    def isFocusing(self, autofocus_device) -> bool:
        status = self._mmc.getProperty(autofocus_device, "State")
        return status == "Focusing"

    def set_offset(self, offset_device, offset: float) -> None:
        self._mmc.setProperty(offset_device, "Position", offset)

    def get_position(self, offset_device) -> float:
        return float(self._mmc.getProperty(offset_device, "Position"))


class NikonPFS(AutofocusDevice):
    """
    for Nikon PFS:
    - mmcore.getAutoFocusDevice() -> "TIPFStatus"
    - offset_device to set/get the PFS offset -> "TIPFSOffset"
      "TIPFSOffset" is listed under StageDevice (z movement).
      Can be used with mmc.setProperty("TIPFSOffset", "Position", offset)
      or mmc.getProperty("TIPFSOffset", "Position")
    """

    offset_device = "TIPFSOffset"
    autofocus_device = "TIPFStatus"

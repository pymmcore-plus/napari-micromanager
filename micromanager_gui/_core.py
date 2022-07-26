"""Functions and utils for managing the global mmcore singleton."""
from __future__ import annotations

from typing import Optional

from pymmcore_plus import CMMCorePlus

_SESSION_CORE: Optional[CMMCorePlus] = None


def get_core_singleton(remote=False) -> CMMCorePlus:
    """Retrieve the MMCore singleton for this session.

    The first call to this function determines whether we're running remote or not.
    perhaps a temporary function for now...
    """
    global _SESSION_CORE
    if _SESSION_CORE is None:
        if remote:
            from pymmcore_plus import RemoteMMCore

            _SESSION_CORE = RemoteMMCore()  # type: ignore  # it has the same interface.
        else:
            _SESSION_CORE = CMMCorePlus.instance()
    return _SESSION_CORE

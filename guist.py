import trio
import sys
import time
import httpx
from outcome import Error
import traceback

# Can't use PySide2 currently because of
# https://bugreports.qt.io/projects/PYSIDE/issues/PYSIDE-1313
from PyQt5 import QtCore, QtWidgets

FPS = 60

import httpcore._async.http11

# Default is 4096
httpcore._async.http11.AsyncHTTP11Connection.READ_NUM_BYTES = 100_000


async def get(url):
    dialog = QtWidgets.QProgressDialog(f"Fetching {url}...", "Cancel", 0, 0)
    # Always show the dialog
    dialog.setMinimumDuration(0)
    with trio.CancelScope() as cscope:
        dialog.canceled.connect(cscope.cancel)
        start = time.monotonic()
        downloaded = 0
        last_screen_update = time.monotonic()
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as response:
                total = 80_300_000
                dialog.setMaximum(total)
                async for chunk in response.aiter_raw():
                    downloaded += len(chunk)
                    if time.monotonic() - last_screen_update > 1 / FPS:
                        dialog.setValue(downloaded)
                        last_screen_update = time.monotonic()
        end = time.monotonic()
        dur = end - start
        bytes_per_sec = downloaded / dur
        print(f"Downloaded {downloaded} bytes in {dur:.2f} seconds")
        print(f"{bytes_per_sec:.2f} bytes/sec")
    return 1


app = QtWidgets.QApplication(sys.argv)

# class Reenter(QtCore.QObject):
#     run = QtCore.Signal(object)

# reenter = Reenter()
# reenter.run.connect(lambda fn: fn(), QtCore.Qt.QueuedConnection)
# run_sync_soon_threadsafe = reenter.run.emit

# This is substantially faster than using a signal... for some reason Qt
# signal dispatch is really slow (and relies on events underneath anyway, so
# this is strictly less work)
REENTER_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())


class ReenterEvent(QtCore.QEvent):
    pass


class Reenter(QtCore.QObject):
    def event(self, event):
        event.fn()
        return False


reenter = Reenter()


def run_sync_soon_threadsafe(fn):
    event = ReenterEvent(REENTER_EVENT)
    event.fn = fn
    app.postEvent(reenter, event)


def done_callback(outcome):
    print(f"Outcome: {outcome}")
    if isinstance(outcome, Error):
        exc = outcome.error
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    print("QUIT!")
    app.quit()


trio.lowlevel.start_guest_run(
    get,
    sys.argv[1],
    run_sync_soon_threadsafe=run_sync_soon_threadsafe,
    done_callback=done_callback,
)

app.exec_()
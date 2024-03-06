# Getting Started

## Installation

### Installing napari-micromanager

```sh
pip install napari-micromanager PyQt5
# you may also pick from PySide2, PyQt6, PySide6 for your Qt backend
```

You will then also need to grab the `Micro-Manager` device adapters

```sh
mmcore install
```

See [`pymmcore-plus` documentation page](https://pymmcore-plus.github.io/pymmcore-plus/install/#installing-micro-manager-device-adapters) for details on the `mmcore` helper command.

## Usage

```sh
napari-micromanager
```

This will open a new napari window with the micromanager plugin enabled.

Select a MM Config file at the top left of the window, then click load.

Then ... much of the rest is hopefully self explanatory :smile:.

Underlying napari-micro-manager is the `pymmcore-plus` package, which is a
python wrapper around `pymmcore` and the C++ CMMCore library (*not*
pycro-manager and not the Java-based MMStudio).  There is much more documentation
available at the `pymmcore-plus` [documentation page](https://pymmcore-plus.github.io/pymmcore-plus/), and widgets in the GUI are all powered by the `pymmcore-widgets` package.
See the `pymmcore-widgets` [documentation page](https://pymmcore-plus.github.io/pymmcore-widgets/) for more details.

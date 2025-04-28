# napari-micromanager

[![License](https://img.shields.io/pypi/l/napari-micromanager.svg?color=green)](https://github.com/napari/napari-micromanager/raw/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-micromanager.svg?color=green)](https://pypi.org/project/napari-micromanager)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-micromanager.svg?color=green)](https://python.org)
[![Tests](https://github.com/pymmcore-plus/napari-micromanager/actions/workflows/ci.yml/badge.svg)](https://github.com/pymmcore-plus/napari-micromanager/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pymmcore-plus/napari-micromanager/branch/main/graph/badge.svg?token=tf6lYDWV1s)](https://codecov.io/gh/pymmcore-plus/napari-micromanager)

GUI interface between napari and micromanager powered by [pymmcore-plus](https://pymmcore-plus.github.io/pymmcore-plus/) and [pymmcore-widgets](https://pymmcore-plus.github.io/pymmcore-widgets/)

> [!NOTE]  
> While this plugin will continue to be maintained, we are focusing current efforts on a napari-independent
> gui (using [ndv](https://github.com/pyapp-kit/ndv)) for reasons of performance and minimizing dependencies.
> Please follow <https://github.com/pymmcore-plus/pymmcore-gui> for details

----------------------------------
<img width="1840" alt="napari-micromanager" src="https://github.com/pymmcore-plus/napari-micromanager/assets/1609449/e1f395cd-2d57-488e-89e2-b1923310fc2a">

## Installation

You can install `napari-micromanager` via [pip]:

    pip install napari-micromanager

You will also need a Qt backend such as PySide2/6, or PyQt5/6.  **PyQt is
preferred and receives more testing**. If you've previously installed napari
into this environment with `pip install napari[all]`, then you will likely
already have it. If not, you will also need to install a Qt backend of your
choice:

    pip install pyqt5  # or any of {pyqt5, pyqt6, pyside2, pyside6}

### Getting micromanager adapters

The easiest way to get the micromanager adapters is to use:

```
mmcore install
```

this will install micromanager to the pymmcore_plus folder in your site-package; use this to see where:

```
python -c "from pymmcore_plus import find_micromanager; print(find_micromanager())"
```

alternatively, you can direct pymmcore_plus to your own micromanager installation with the `MICROMANAGER_PATH`
environment variable:

```
export MICROMANAGER_PATH='/path/to/Micro-Manager-...'
```

## Contributing

Contributions are very welcome.

### Launching napari with plugin

You can launch napari and automatically load this plugin using the `launch-dev.py` script:

```bash
python launch-dev.py
```

Alternatively you can run:

```bash
napari -w napari-micromanager
```

## License

Distributed under the terms of the [BSD-3] license,
"napari-micromanager" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[file an issue]: https://github.com/pymmcore-plus/napari-micromanager/issues
[pip]: https://pypi.org/project/pip/

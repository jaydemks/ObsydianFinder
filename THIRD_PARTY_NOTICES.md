# Third party notices

Obsydian Finder's original source is licensed under MIT. This does not replace the licenses of its dependencies.

## Three.js 0.180.0

The bundled renderer and OrbitControls are MIT licensed. See [vendor/THREE-LICENSE.txt](vendor/THREE-LICENSE.txt) and the [upstream source](https://github.com/mrdoob/three/tree/r180). The bundle is built locally; the application uses no rendering CDN.

## PySide6, Shiboken6 and Qt 6.11.2

Desktop builds include dynamically linked Qt libraries and the PySide6 bindings from the official PyPI wheels. These components have LGPLv3, GPLv3 and component-specific terms. Applicable license texts are included in `licenses`, including [LGPLv3](licenses/LGPL-3.0.txt) and [GPLv3](licenses/GPL-3.0.txt). Wheel license directories are copied into packaged builds.

Corresponding upstream sources: [Qt for Python 6.11.2](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/), [Qt 6.11.2](https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/) and [Qt source repositories](https://code.qt.io/cgit/qt/). No changes to these libraries are made by this project. The build specification and pinned dependencies are included so users can rebuild the application with modified libraries. The application is distributed as a directory bundle with separate shared libraries. Nothing in Obsydian Finder's license restricts modification or reverse engineering needed to debug modifications to these libraries.

Qt WebEngine incorporates Chromium and other third party code under their respective licenses. See [Chromium's license](licenses/Chromium-LICENSE.txt), the [included component notices](licenses/Chromium-CREDITS.html), the Qt WebEngine source distribution and its `src/3rdparty/chromium` notices. The native Help menu opens the included notices for offline reading.

## Python and packaging

Standalone archives contain the Python runtime under the Python Software Foundation license; its license is copied to `licenses/Python` when supplied by the build environment. See [Python licensing](https://docs.python.org/3/license.html).

PyInstaller is used to build the archives under GPL with its bootloader exception permitting distribution of the resulting application. See [PyInstaller licensing](https://pyinstaller.org/en/stable/license.html). Build tooling is pinned in `requirements.txt`.

# Usage and source setup

## Scanning and connections

Scanning is asynchronous. You can navigate and search collected results during a scan; file mutations wait until scanning stops. System folders are optional and read only in the explorer. Access restrictions and excluded folders are counted in the interface.

Sizes are logical file sizes, not exact physical disk allocation. Hard links, compressed files, sparse files and snapshots can make totals differ from the operating system. Folder colors represent relative size, because folders do not have a fixed capacity. Drive colors represent used capacity.

The automatic reference index reads supported text, code and configuration formats and resolves local paths against scanned files. It does not execute scanned content. Binary dependencies, runtime loading and every operating system relationship are outside its scope. Potential duplicate candidates require the explicit duplicate check before being treated as identical.

Reference indexing is bounded to 1 MiB per file, 64 MiB of text and 20,000 text files per scan, with up to 50,000 edges. Recognized credential paths are skipped. The inspector reports evidence; a connection does not imply that a file can safely be removed. The 3D view caps visible links at 48 to remain readable and shows a visible/available count.

Application discovery uses Windows uninstall registry records, macOS application bundles, and Linux desktop/package metadata. Windows Store applications and installations without suitable metadata may be absent. Components mean declared installation locations, not every registry entry, shared library or user setting. Windows uses the registered interactive uninstaller; Linux delegates to a supported package manager. macOS opens Finder for manual removal. The confirmation explains the action before it runs.

## Native window

The app embeds its local interface using Qt WebEngine and serves it only on loopback. It does not open a browser at startup. The packaged app has no command window. An explicit Linux package removal may open the package manager in a terminal for authentication and confirmation.

Tray support depends on the desktop environment. When unavailable, closing the window exits. WebGL requires compatible graphics support. Scan/session data and embedded web cache live in the platform's local application data directory; the app does not upload scanned files.

## Run from source

Use Python 3.11. Create a virtual environment named `.venv` in the project and install `requirements.txt` into it. On Windows:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then double-click **Start Obsydian.vbs**. It opens the packaged application if present, otherwise starts the source application without a console window.

On macOS and Linux:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python launch.py
```

For normal use without a terminal, download the packaged application. Linux Qt requires the system libraries installed by the [build workflow](../.github/workflows/desktop-build.yml). The current Linux archive targets Ubuntu 24.04 or compatible systems, not every distribution. The macOS archive targets Apple silicon; Intel users can build from source on their own Mac.

## Build and verify

Run these commands with the virtual environment's Python on the target operating system:

```sh
python -m unittest discover -s tests -p "test_*.py"
python -m PyInstaller --noconfirm Obsydian.spec
```

The output is in `dist`. Distribute the complete directory or `.app`, including dynamic libraries and license files. The GitHub workflow archives this output. Browser integration tests in `tests/ui_webgl.py` and `tests/ui_applications.py` additionally need Selenium and Chrome; they use temporary fixtures and simulated uninstall actions.

The local Three.js bundle uses Three.js 0.180.0. To rebuild it, install `three@0.180.0` and `esbuild@0.25.10` under `.vendor-build`, then bundle `tools/vendor-entry.js` into `vendor/three.bundle.js` with esbuild. No CDN is required at runtime.

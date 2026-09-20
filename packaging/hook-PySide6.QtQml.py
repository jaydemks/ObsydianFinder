"""WebEngineWidgets needs QtQml libraries, but this app loads no QML documents.

Do not collect Qt's entire optional QML plugin tree (charts, graphs, 3D, etc.).
The normal dependency helper still collects all directly linked Qt libraries.
"""
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

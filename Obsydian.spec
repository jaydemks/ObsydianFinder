# Native, windowed, onedir bundle. Build this spec on each target OS.
from pathlib import Path
import sys
import PySide6
import hashlib
root = Path(SPECPATH)
digest = hashlib.sha256()
for source in sorted(root.iterdir()):
    if source.suffix in ('.py', '.js', '.html', '.css'):
        digest.update(source.name.encode())
        digest.update(source.read_bytes())
(root / 'build').mkdir(exist_ok=True)
build_version = root / 'build' / 'build-version.txt'
build_version.write_text(digest.hexdigest()[:16], encoding='ascii')
assets = [(str(p), '.') for p in root.iterdir() if p.suffix in ('.html', '.js', '.css', '.svg')]
assets.append((str(build_version), '.'))
assets += [(str(root / 'assets'), 'assets')]
assets += [(str(root / 'vendor'), 'vendor')]
assets += [(str(root / 'licenses'), 'licenses')]
assets += [(str(root / 'docs'), 'docs')]
for distribution in Path(PySide6.__file__).parent.parent.glob('*6.11.2.dist-info'):
    if (distribution / 'licenses').exists():
        assets.append((str(distribution / 'licenses'), 'licenses/' + distribution.name))
assets += [(str(root / name), '.') for name in ('README.md', 'THIRD_PARTY_NOTICES.md', 'LICENSE') if (root / name).exists()]
if (Path(sys.base_prefix) / 'LICENSE.txt').exists():
    assets.append((str(Path(sys.base_prefix) / 'LICENSE.txt'), 'licenses/Python'))
icon = root / 'assets' / ('obsydian.icns' if sys.platform == 'darwin' else 'obsydian.ico')
a = Analysis(['desktop.py'], pathex=[str(root)], binaries=[], datas=assets,
             hiddenimports=[], hookspath=[str(root / 'packaging')], runtime_hooks=[], excludes=['tkinter', 'unittest'], noarchive=False)
if sys.platform == 'win32':
    # Qt on Windows uses the OS ICU API. Do not shadow it with unrelated ICU
    # DLLs discovered on a developer PATH (for example Poppler or Conda).
    a.binaries = [(name, source, kind) for name, source, kind in a.binaries
                  if not (Path(name).name.lower().startswith('icu') and name.lower().endswith('.dll'))]
    # Python 3.11 ships an older VC runtime. Qt 6.11 needs the newer compatible
    # runtime shipped in the PySide wheel; use it at the DLL search root too.
    qt_directory = Path(PySide6.__file__).parent
    a.binaries = [(name, str(qt_directory / name.lower()), kind)
                  if name.upper() in ('VCRUNTIME140.DLL', 'VCRUNTIME140_1.DLL')
                  else (name, source, kind) for name, source, kind in a.binaries]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Obsydian Finder',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(icon) if icon.exists() else None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Obsydian Finder')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='Obsydian Finder.app', icon=str(icon) if icon.exists() else None,
                 bundle_identifier='app.obsydian.finder',
                 info_plist={'NSHighResolutionCapable': True, 'CFBundleShortVersionString': '0.5.2'})

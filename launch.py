"""Start one local Obsydian instance, or reopen its browser window."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
if os.environ.get('OBSYDIAN_DATA_DIR'):
    DATA_DIR = Path(os.environ['OBSYDIAN_DATA_DIR'])
elif sys.platform == 'win32':
    DATA_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'ObsydianFinder'
elif sys.platform == 'darwin':
    DATA_DIR = Path.home() / 'Library' / 'Application Support' / 'ObsydianFinder'
else:
    DATA_DIR = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'obsydian-finder'
SESSION = DATA_DIR / '.obsydian-session.json'

def version():
    if getattr(sys, 'frozen', False) and (BASE / 'build-version.txt').exists():
        return (BASE / 'build-version.txt').read_text(encoding='ascii').strip()
    digest = hashlib.sha256()
    for path in sorted(BASE.iterdir()):
        if path.suffix in ('.py', '.js', '.html', '.css'):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]

def current():
    try:
        data = json.loads(SESSION.read_text(encoding='utf-8'))
        if not isinstance(data['port'], int) or not 1 <= data['port'] <= 65535:
            return None
        url = f"http://127.0.0.1:{data['port']}"
        request = urllib.request.Request(url + '/api/info', headers={'X-Obsydian-Token': data['token']})
        with urllib.request.urlopen(request, timeout=1) as response:
            info = json.load(response)
        if info.get('app') == 'obsydian-finder' and info.get('pid') == data['pid']:
            return dict(data, url=url, version=info['version'], desktop=info.get('desktop', False))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None

def save_session(port, token):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(SESSION, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        json.dump(dict(port=port, token=token, pid=os.getpid()), stream)

def instance_lock():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(DATA_DIR / '.obsydian-instance.lock', 'a+b')
    if os.name == 'nt':
        import msvcrt
        handle.seek(0)
        if not handle.read(1):
            handle.write(b'1')
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            return None
    else:
        import fcntl
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return None
    return handle

def main():
    # Dependencies are imported here so the HTTP service remains stdlib-only.
    try:
        from desktop import main as desktop_main
    except ImportError as exc:
        raise RuntimeError('Desktop components are missing. Use the packaged Obsydian Finder app, or install requirements.txt in the project environment.') from exc
    desktop_main()

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), 'Obsydian Finder', 0x10)
        else:
            print(str(exc), file=sys.stderr)
        sys.exit(1)

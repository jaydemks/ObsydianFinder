"""Launch the packaged native window against an isolated profile, then exit."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

project = Path(__file__).resolve().parents[1]
if sys.platform == 'darwin':
    executable = project / 'dist/Obsydian Finder.app/Contents/MacOS/Obsydian Finder'
elif sys.platform == 'win32':
    executable = project / 'dist/Obsydian Finder/Obsydian Finder.exe'
else:
    executable = project / 'dist/Obsydian Finder/Obsydian Finder'
with tempfile.TemporaryDirectory(prefix='obsydian-native-') as temporary:
    directory = Path(temporary).resolve()
    screenshot = directory / 'window.png'
    environment = dict(os.environ, OBSYDIAN_DATA_DIR=str(directory / 'profile'),
                       OBSYDIAN_SMOKE_SCREENSHOT=str(screenshot))
    process = subprocess.Popen([str(executable)], env=environment)
    try:
        result = process.wait(timeout=50)
        report = json.loads(screenshot.with_suffix('.json').read_text())
        assert result == 0, result
        assert screenshot.exists(), 'Native window did not render'
        assert report['ready'], 'Native interface scripts did not load'
        assert report['restoreShows'], report
        if report['trayAvailable']:
            assert report['closeHides'], report
        print(json.dumps({'native_desktop': 'passed', **report}))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)

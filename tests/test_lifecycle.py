import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request


class LifecycleTests(unittest.TestCase):
    def test_single_instance_and_authenticated_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = Path(__file__).resolve().parents[1]
            for name in ('server.py', 'references.py', 'windows_recycle.py', 'launch.py', 'apps.py'):
                shutil.copy2(source / name, root / name)
            command = [sys.executable, str(root / 'server.py'), '--no-browser', '--port', '0']
            environment = dict(os.environ, OBSYDIAN_DATA_DIR=str(root))
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=environment)
            try:
                session = root / '.obsydian-session.json'
                deadline = time.monotonic() + 10
                while not session.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(session.exists(), 'Server did not create its session file')
                data = json.loads(session.read_text(encoding='utf-8'))
                duplicate = subprocess.run(command, capture_output=True, timeout=10, env=environment)
                self.assertEqual(duplicate.returncode, 0, duplicate.stderr.decode(errors='replace'))
                self.assertEqual(json.loads(session.read_text(encoding='utf-8'))['pid'], data['pid'])
                self.assertIsNone(process.poll())
                request = urllib.request.Request(f"http://127.0.0.1:{data['port']}/api/shutdown", data=b'{}',
                                                  headers={'X-Obsydian-Token': data['token']})
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertTrue(json.load(response)['ok'])
                self.assertEqual(process.wait(timeout=10), 0)
                self.assertFalse(session.exists())
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                process.stderr.close()


if __name__ == '__main__':
    unittest.main()


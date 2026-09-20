"""Deterministic streaming checks: late targets, one read per source, cancellation."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from server import Store


class ControlledScan(Store):
    def __init__(self):
        super().__init__()
        self.add_target = threading.Event()
        self.finish_scan = threading.Event()

    def scan(self, roots):
        root = Path(roots[0])
        def add(path, directory=False):
            key = str(path)
            with self.lock:
                self.keys.append(key)
                self.nodes[key] = dict(path=key, name=path.name, isDir=directory,
                                       ext=path.suffix, size=0 if directory else path.stat().st_size,
                                       children=[], parent=None if directory else str(root),
                                       partial=directory, readOnly=False)
                if not directory:
                    self.nodes[str(root)]['children'].append(key)
        add(root, True)
        add(root / 'source.md')
        while not self.add_target.is_set() and not self.cancel_event.wait(.01):
            pass
        if not self.cancel_event.is_set():
            add(root / 'later.bin')
        while not self.finish_scan.is_set() and not self.cancel_event.wait(.01):
            pass
        with self.lock:
            self.state.update(running=False, complete=not self.cancel_event.is_set(),
                              cancelled=self.cancel_event.is_set())


class StreamingReferences(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / 'source.md').write_text('[later](later.bin)', encoding='utf8')
        (self.root / 'later.bin').write_bytes(b'data')
        self.store = ControlledScan()

    def until(self, check):
        deadline = time.monotonic() + 5
        while not check() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(check())

    def tearDown(self):
        self.store.cancel()
        self.until(lambda: not self.store.state['running'])
        self.until(lambda: not self.store.references.status()['running'])
        self.temp.cleanup()

    def test_resolves_target_published_later_without_rereading_source(self):
        read = self.store.references.read
        with patch.object(self.store.references, 'read', wraps=read) as observed:
            self.store.start(str(self.root))
            self.until(lambda: self.store.references.status()['files'] == 1)
            self.assertTrue(self.store.state['running'])
            self.assertEqual(self.store.references.status()['edges'], 0)
            # Mutations can leave an earlier path entry in the append-only feed.
            with self.store.lock:
                self.store.keys.append(str(self.root / 'source.md'))
            self.store.add_target.set()
            self.until(lambda: self.store.references.status()['edges'] == 1)
            self.assertTrue(self.store.state['running'])
            self.assertTrue(self.store.references.status()['running'])
            self.store.finish_scan.set()
            self.until(lambda: self.store.references.status()['complete'])
            self.assertEqual(observed.call_count, 1)
        self.assertEqual(self.store.references.query(str(self.root))['count'], 1)

    def test_single_stop_cancels_scan_and_reference_worker(self):
        self.store.start(str(self.root))
        self.until(lambda: self.store.references.status()['files'] == 1)
        self.store.cancel()
        self.until(lambda: not self.store.references.status()['running'])
        self.until(lambda: not self.store.state['running'])
        self.assertTrue(self.store.references.status()['cancelled'])
        self.assertFalse(self.store.references.status()['complete'])

    def test_new_scan_invalidates_pending_edges(self):
        self.store.start(str(self.root))
        self.until(lambda: self.store.references.status()['files'] == 1)
        self.store.cancel()
        self.until(lambda: not self.store.state['running'])
        (self.root / 'source.md').write_text('No references now.', encoding='utf8')
        self.store.add_target.set()
        self.store.finish_scan.set()
        self.store.start(str(self.root))
        self.until(lambda: self.store.references.status()['complete'])
        self.assertEqual(self.store.references.status()['edges'], 0)
        self.assertEqual(self.store.references.query(str(self.root))['count'], 0)


if __name__ == '__main__':
    unittest.main()


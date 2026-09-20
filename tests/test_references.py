import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from server import Store


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / 'src').mkdir()
        (self.root / 'assets').mkdir()
        (self.root / 'assets' / 'logo.svg').write_text('<svg/>', encoding='utf-8')
        (self.root / 'src' / 'helper.ts').write_text('export const answer = 42;', encoding='utf-8')
        (self.root / 'src' / 'app.ts').write_text('import "./helper";\nconst image = "../assets/logo.svg";', encoding='utf-8')
        (self.root / 'README.md').write_text('[App](src/app.ts)\n[Missing](missing.txt)\n[Remote](https://example.org/src/app.ts)', encoding='utf-8')
        self.store = Store()
        self.scan()

    def tearDown(self):
        self.store.references.cancel()
        self.wait(lambda: self.store.references.status()['running'])
        self.temp.cleanup()

    def wait(self, running):
        deadline = time.monotonic() + 5
        while running() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(running())

    def scan(self):
        self.store.start(str(self.root))
        self.wait(lambda: self.store.state['running'])
        self.wait(lambda: self.store.references.status()['running'])

    def index(self):
        self.store.references.start()
        self.wait(lambda: self.store.references.status()['running'])

    def test_resolved_incoming_outgoing_and_cross_folder_edges(self):
        self.index()
        result = self.store.references.query(str(self.root / 'src'))
        pairs = {(Path(e['source']).name, Path(e['target']).name) for e in result['edges']}
        self.assertEqual(pairs, {('app.ts', 'helper.ts'), ('app.ts', 'logo.svg'), ('README.md', 'app.ts')})
        for edge in result['edges']:
            self.assertEqual(edge['confidence'], 'resolved')
            self.assertEqual(edge['kind'], 'reference')
            self.assertTrue(edge['evidence'].startswith('line '))
            self.assertNotIn('const image', edge['evidence'])
        self.assertEqual(self.store.references.query(str(self.root / 'src' / 'app.ts'))['count'], 3)

    def test_limits_secret_files_and_external_references(self):
        (self.root / '.env').write_text('"src/app.ts"', encoding='utf-8')
        (self.root / 'credentials.json').write_text('"src/app.ts"', encoding='utf-8')
        (self.root / 'large.txt').write_bytes(b'x' * (1024 * 1024 + 1))
        self.scan()
        opened = []
        actual = self.store.references.read
        def observed(path, remaining):
            opened.append(path.name)
            return actual(path, remaining)
        with patch.object(self.store.references, 'read', side_effect=observed):
            self.index()
        self.assertNotIn('.env', opened)
        self.assertNotIn('credentials.json', opened)
        self.assertNotIn('large.txt', opened)
        self.assertGreaterEqual(self.store.references.status()['skipped'], 3)
        with patch.object(self.store.references, 'MAX_FILES', 1):
            self.index()
            self.assertEqual(self.store.references.status()['files'], 1)
            self.assertTrue(self.store.references.status()['limited'])

    def test_cancel_and_new_scan_invalidate_background_job(self):
        reached, release = threading.Event(), threading.Event()
        actual = self.store.references.read
        def pause(path, remaining):
            reached.set()
            release.wait(5)
            return actual(path, remaining)
        with patch.object(self.store.references, 'read', side_effect=pause):
            self.store.references.start()
            try:
                self.assertTrue(reached.wait(5))
                self.store.references.cancel()
            finally:
                release.set()
            self.wait(lambda: self.store.references.status()['running'])
        self.assertTrue(self.store.references.status()['cancelled'])
        self.assertFalse(self.store.references.status()['complete'])
        self.index()
        self.assertGreater(self.store.references.query(str(self.root))['count'], 0)
        self.scan()
        self.assertFalse(self.store.references.status()['stale'])
        self.assertTrue(self.store.references.status()['complete'])
        self.assertGreater(self.store.references.query(str(self.root))['count'], 0)

    def test_preview_limits_and_partial_fields(self):
        for index in range(12):
            (self.root / 'assets' / ('item-%02d.bin' % index)).write_bytes(b'x' * index)
        self.scan()
        preview = self.store.previews(str(self.root))['previews'][str(self.root / 'assets')]
        self.assertEqual(len(preview['items']), 8)
        self.assertEqual(preview['count'], 13)
        self.assertFalse(preview['partial'])
        sizes = [item['size'] for item in preview['items']]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_replaced_source_symlink_is_not_read(self):
        source = self.root / 'README.md'
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'outside.md'
            target.write_text('"' + str(self.root / 'src' / 'app.ts') + '"', encoding='utf-8')
            source.unlink()
            try:
                source.symlink_to(target)
            except OSError:
                self.skipTest('Symlinks unavailable for this account')
            self.index()
            self.assertGreater(self.store.references.status()['errors'], 0)
            edges = self.store.references.query(str(self.root))['edges']
            self.assertFalse(any(edge['source'] == str(source) for edge in edges))


if __name__ == '__main__':
    unittest.main()


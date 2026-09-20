import tempfile
import time
import unittest
import http.client
import threading
from unittest.mock import patch
from pathlib import Path
from server import Store, Handler, ThreadingHTTPServer


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / 'folder').mkdir()
        (self.root / 'a.txt').write_bytes(b'hello')
        (self.root / 'folder' / 'b.txt').write_bytes(b'hello')
        (self.root / 'different.txt').write_bytes(b'world')
        self.store = Store()
        self.refresh()

    def tearDown(self):
        self.temp.cleanup()

    def refresh(self):
        self.store.start(str(self.root))
        self.wait()

    def wait(self):
        end = time.monotonic() + 5
        while self.store.state['running'] and time.monotonic() < end:
            time.sleep(.01)
        self.assertFalse(self.store.state['running'])

    def test_aggregate_and_exact_duplicates(self):
        listing = self.store.children(str(self.root))
        self.assertEqual(listing['total'], 15)
        self.assertEqual(self.store.state['files'], 3)
        duplicates = self.store.duplicates(str(self.root / 'a.txt'))
        self.assertEqual([n['name'] for n in duplicates['items']], ['b.txt'])

    def test_mutation_rejects_escape_root_and_overwrite(self):
        for data in [
            dict(action='rename', path=str(self.root), name='new'),
            dict(action='rename', path=str(self.root / 'a.txt'), name='../escape'),
            dict(action='rename', path=str(self.root / 'a.txt'), name='different.txt'),
            dict(action='move', path=str(self.root / 'a.txt'), destination=str(self.root.parent)),
            dict(action='move', path=str(self.root / 'folder'), destination=str(self.root / 'folder')),
        ]:
            with self.assertRaises(ValueError):
                self.store.action(data)
        self.assertEqual((self.root / 'a.txt').read_bytes(), b'hello')

    def test_rename_and_move_refresh(self):
        self.store.action(dict(action='rename', path=str(self.root / 'a.txt'), name='renamed.txt'))
        self.wait()
        self.assertTrue((self.root / 'renamed.txt').exists())
        self.store.action(dict(action='move', path=str(self.root / 'renamed.txt'), destination=str(self.root / 'folder')))
        self.wait()
        self.assertTrue((self.root / 'folder' / 'renamed.txt').exists())
        self.assertEqual(self.store.state['bytes'], 15)

    def test_protected_directory_excluded(self):
        (self.root / 'Windows').mkdir()
        (self.root / 'Windows' / 'system.txt').write_bytes(b'secret')
        self.refresh()
        self.assertEqual(self.store.state['excluded'], 1)
        self.assertEqual(self.store.state['bytes'], 15)
        with self.assertRaises(ValueError):
            self.store.checked(str(self.root / 'Windows' / 'system.txt'))

    def test_symlinks_never_followed(self):
        link = self.root / 'link'
        try:
            link.symlink_to(self.root / 'folder', target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation unavailable on this Windows account')
        self.refresh()
        self.assertEqual(self.store.state['excluded'], 1)
        self.assertEqual(self.store.state['bytes'], 15)
        with self.assertRaises(ValueError):
            self.store.checked(str(link / 'b.txt'))

    def test_system_inclusive_scan_is_read_only(self):
        folder = self.root / 'Windows'
        folder.mkdir()
        (folder / 'system.txt').write_bytes(b'secret')
        self.store.start(str(self.root), include_system=True)
        self.wait()
        self.assertEqual(self.store.state['bytes'], 21)
        listing = self.store.children(str(folder))
        self.assertTrue(listing['items'][0]['readOnly'])
        self.assertFalse(listing['partial'])
        with self.assertRaises(ValueError):
            self.store.action(dict(action='rename', path=str(folder / 'system.txt'), name='new.txt'))

    def test_total_roots_deduplicate_overlap_and_ignore_home_alias(self):
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / 'disk.bin').write_bytes(b'1234567')
            mocked = [dict(path=str(self.root / 'folder'), isDisk=True),
                      dict(path=str(self.root), isDisk=True),
                      dict(path=str(self.root), isDisk=False),
                      dict(path=str(Path(other).resolve()), isDisk=True)]
            with patch('server.drives', return_value=mocked):
                self.store.start(all_disks=True, include_system=True)
                self.wait()
                self.assertEqual(self.store.state['bytes'], 22)
                listing = self.store.children('@computer')
                self.assertEqual(listing['count'], 2)
                self.assertFalse(listing['partial'])
                self.assertEqual(listing['total'], 22)
                self.assertEqual(self.store.children(str(self.root))['parent'], '@computer')
                # Mutations preserve the total scan configuration.
                self.store.action(dict(action='rename', path=str(self.root / 'a.txt'), name='new.txt'))
                self.wait()
                self.assertEqual(self.store.state['mode'], 'all')
                self.assertTrue(self.store.state['includeSystem'])
                self.assertEqual(self.store.state['bytes'], 22)

    def test_live_results_and_cancel_preserve_partial_tree(self):
        import server
        for i in range(220):
            (self.root / ('stream-%03d.bin' % i)).write_bytes(b'x')
        reached, release = threading.Event(), threading.Event()
        actual_scandir = server.os.scandir

        class PausedEntries:
            def __init__(self, entries):
                self.entries, self.count = entries, 0

            def __next__(self):
                self.count += 1
                if self.count == 120:
                    reached.set()
                    if not release.wait(5):
                        raise OSError('Test barrier timeout')
                return next(self.entries)

            def close(self):
                self.entries.close()

        def scandir(path):
            entries = actual_scandir(path)
            return PausedEntries(entries) if Path(path) == self.root else entries

        with patch('server.os.scandir', side_effect=scandir):
            self.store.start(str(self.root))
            try:
                self.assertTrue(reached.wait(5))
                status = self.store.status()
                self.assertTrue(status['running'])
                self.assertGreater(status['files'], 0)
                listing = self.store.children(str(self.root))
                self.assertTrue(listing['partial'])
                self.assertGreater(listing['count'], 0)
                self.assertEqual(listing['total'], status['bytes'])
                self.assertGreater(self.store.search('stream')['count'], 0)
                self.store.cancel()
            finally:
                release.set()
            self.wait()
        self.assertTrue(self.store.state['cancelled'])
        self.assertFalse(self.store.state['complete'])
        self.assertGreater(self.store.state['bytes'], 0)
        self.assertLess(self.store.state['files'], 223)
        self.assertTrue(self.store.children(str(self.root))['partial'])
        indexed_file = next(item for item in self.store.children(str(self.root))['items']
                            if not item['isDir'])
        self.store.action(dict(action='rename', path=indexed_file['path'], name='new.txt'))
        self.assertFalse(self.store.state['running'])
        with self.assertRaises(ValueError):
            self.store.duplicates(indexed_file['path'])

    def test_incremental_move_and_external_removal_do_not_rescan(self):
        with patch.object(self.store, 'start', side_effect=AssertionError('Unexpected full scan')):
            self.store.action(dict(action='move', path=str(self.root / 'a.txt'), destination=str(self.root / 'folder')))
            self.assertEqual(self.store.children(str(self.root / 'folder'))['total'], 10)
            self.assertEqual(self.store.state['bytes'], 15)
            (self.root / 'folder' / 'a.txt').unlink()
            listing = self.store.children(str(self.root / 'folder'))
            self.assertEqual(listing['count'], 1)
            self.assertEqual(listing['total'], 5)
            self.assertEqual(self.store.state['bytes'], 10)
            self.assertEqual(self.store.state['files'], 2)

    def test_batch_recycle_success_missing_failure_prunes_only_success(self):
        missing = self.root / 'a.txt'
        missing.unlink()
        def fake_recycle(path):
            if path.name == 'different.txt':
                raise OSError('Fixture recycle failure')
            path.unlink()
        with patch('server.recycle', side_effect=fake_recycle), patch.object(self.store, 'start', side_effect=AssertionError('Unexpected full scan')):
            result = self.store.actions(dict(action='trash', paths=[str(missing), str(self.root / 'folder' / 'b.txt'), str(self.root / 'different.txt'), str(self.root)]))
        self.assertEqual([r['ok'] for r in result['results']], [True, True, False, False])
        self.assertTrue(result['results'][0]['missing'])
        self.assertEqual(self.store.state['files'], 1)
        self.assertEqual(self.store.state['bytes'], 5)
        self.assertTrue((self.root / 'different.txt').exists())

    @unittest.skipUnless(__import__('sys').platform == 'win32', 'Windows-only integration')
    def test_actual_windows_recycle_disposable_file(self):
        disposable = self.root / 'obsydian-recycle-test.txt'
        disposable.write_text('Disposable Obsydian integration test fixture.', encoding='utf-8')
        self.refresh()
        result = self.store.actions(dict(action='trash', paths=[str(disposable)]))
        self.assertTrue(result['results'][0]['ok'], result)
        self.assertFalse(disposable.exists())
        self.assertNotIn(str(disposable), self.store.nodes)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.http.store = Store()
        self.http.token = 'test-session-token'
        self.worker = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.worker.join()

    def request(self, headers):
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port)
        conn.request('GET', '/api/status', headers=headers)
        response = conn.getresponse()
        response.read()
        status = response.status
        conn.close()
        return status

    def test_token_required_even_on_get(self):
        self.assertEqual(self.request({}), 403)
        self.assertEqual(self.request({'X-Obsydian-Token': self.http.token}), 200)

    def test_origin_and_host_rejected(self):
        token = {'X-Obsydian-Token': self.http.token}
        self.assertEqual(self.request(dict(token, Host='evil.example')), 403)
        self.assertEqual(self.request(dict(token, Origin='https://evil.example')), 403)


if __name__ == '__main__':
    unittest.main()


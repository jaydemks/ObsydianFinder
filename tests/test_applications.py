import sys
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from apps import ApplicationCatalog, interactive_windows_command


class ApplicationTests(unittest.TestCase):
    def test_mac_bundle_metadata_only_reveals_declared_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'Fixture.app'
            (bundle / 'Contents').mkdir(parents=True)
            with (bundle / 'Contents/Info.plist').open('wb') as stream:
                plistlib.dump({'CFBundleName':'Fixture','CFBundleIdentifier':'test.fixture',
                              'CFBundleShortVersionString':'2.0'}, stream)
            catalog = ApplicationCatalog()
            catalog.mac([Path(directory)])
            item = next(iter(catalog.items.values()))
            self.assertEqual(item['version'], '2.0')
            self.assertEqual(item['_argv'], ['/usr/bin/open','-R',str(bundle)])
            self.assertEqual(item['components'][0]['path'], str(bundle))

    def test_linux_desktop_exec_is_never_used_for_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            desktop = Path(directory) / 'fixture.desktop'
            desktop.write_text('[Desktop Entry]\nType=Application\nName=Fixture\nExec=sh -c "unsafe command"\n', encoding='utf8')
            paths = {name:'/usr/bin/'+name for name in ['dpkg-query','apt','sudo','xterm']}
            result = Mock(stdout='fixture-package: '+str(desktop)+'\n', returncode=0)
            catalog = ApplicationCatalog()
            with patch('apps.shutil.which', side_effect=lambda name:paths.get(name)), patch('apps.subprocess.run', return_value=result) as query:
                catalog.linux([Path(directory)])
            item = next(iter(catalog.items.values()))
            self.assertEqual(item['_argv'], ['/usr/bin/xterm','-e','/usr/bin/sudo','/usr/bin/apt','remove','--','fixture-package'])
            self.assertEqual(item['components'], [])
            query.assert_called_once()

    def test_explicit_confirmation_and_known_id_are_required(self):
        catalog = ApplicationCatalog()
        catalog.add('fixture', 'Fixture', method='Official uninstaller', argv=['fixture.exe'])
        identity = next(iter(catalog.items))
        with patch('apps.shell_execute') as windows, patch('apps.subprocess.Popen') as other:
            for request in [{'id': identity}, {'id': identity, 'confirm': 'true'}, {'id': 'missing', 'confirm': True}]:
                with self.assertRaises(ValueError):
                    catalog.uninstall(request)
            windows.assert_not_called();other.assert_not_called()

    def test_only_cached_command_can_be_launched(self):
        catalog = ApplicationCatalog()
        catalog.add('fixture', 'Fixture', method='Official uninstaller', argv=['fixture.exe', 'arg with spaces'])
        identity = next(iter(catalog.items))
        with patch('apps.shell_execute') as windows, patch('apps.subprocess.Popen') as other:
            result = catalog.uninstall({'id':identity,'confirm':True,'command':'malicious override'})
            self.assertTrue(result['launched'])
            if sys.platform == 'win32':
                windows.assert_called_once_with('fixture.exe', ['arg with spaces'])
                other.assert_not_called()
            else:
                other.assert_called_once_with(['fixture.exe', 'arg with spaces'], shell=False)

    def test_inventory_exposes_evidence_not_private_launch_data(self):
        catalog = ApplicationCatalog()
        catalog.loaded = True
        catalog.add('fixture', 'Fixture', install_path=str(Path.cwd()), size=1024,
                    method='Official uninstaller', argv=['fixture.exe'])
        item = catalog.list()['items'][0]
        self.assertNotIn('_argv', item)
        self.assertEqual(item['components'][0]['kind'], 'installation location')
        self.assertEqual(item['size'], 1024)
        self.assertTrue(item['sizeEstimated'])

    @unittest.skipUnless(sys.platform == 'win32', 'Uses the Windows command-line parser')
    def test_registry_command_is_interactive_and_never_shell_interpreted(self):
        with patch.object(Path, 'is_file', return_value=True):
            args = interactive_windows_command(r'"C:\Program Files\Fixture\uninstall.exe" /S /quiet "a&b"')
            self.assertEqual(args, [r'C:\Program Files\Fixture\uninstall.exe', 'a&b'])
            msi = interactive_windows_command('MsiExec.exe /I{11111111-1111-1111-1111-111111111111} /qn /norestart')
            self.assertIn('/x{11111111-1111-1111-1111-111111111111}', msi)
            self.assertNotIn('/qn', msi)
            self.assertIn('/norestart', msi)
            self.assertIsNone(interactive_windows_command('cmd.exe /c del something'))
            self.assertIsNone(interactive_windows_command('C:\\Program Files\\uninstall.exe /S'))
            self.assertIsNone(interactive_windows_command('bad\ncommand.exe'))

    @unittest.skipUnless(sys.platform == 'win32', 'Read-only Windows inventory')
    def test_real_discovery_is_read_only(self):
        catalog = ApplicationCatalog()
        with patch('apps.shell_execute') as windows, patch('apps.subprocess.Popen') as process:
            catalog.discover()
            windows.assert_not_called();process.assert_not_called()
        self.assertTrue(catalog.loaded)
        self.assertFalse(catalog.running)
        self.assertTrue(all(item['name'] and item['id'] for item in catalog.items.values()))


if __name__ == '__main__':
    unittest.main()


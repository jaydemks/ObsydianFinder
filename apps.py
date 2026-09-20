"""Installed-application metadata and explicit, interactive official removal entry points.

Discovery never runs uninstall commands. File ownership is not inferred from names.
"""
import configparser
import ctypes
import hashlib
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import threading

QUIET = {'/quiet', '/silent', '/verysilent', '/s', '/q', '/qn', '/qb', '/passive',
         '-silent', '--silent', '--quiet', '/suppressmsgboxes'}
BLOCKED_LAUNCHERS = {'cmd.exe', 'powershell.exe', 'pwsh.exe', 'wscript.exe', 'cscript.exe',
                    'mshta.exe', 'rundll32.exe', 'regsvr32.exe'}


def windows_argv(command):
    """Use Windows' command-line parser; never send registry text through a shell."""
    from ctypes import wintypes
    parse = ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    parse.restype = ctypes.POINTER(wintypes.LPWSTR)
    count = ctypes.c_int()
    result = parse(command, ctypes.byref(count))
    if not result:
        raise ValueError('The official uninstall command could not be parsed.')
    try:
        return [result[i] for i in range(count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(result)


def interactive_windows_command(command):
    if not command or any(c in command for c in '\r\n\0'):
        return None
    args = windows_argv(os.path.expandvars(command.strip()))
    if not args:
        return None
    executable = Path(args[0])
    name = executable.name.casefold()
    if name in BLOCKED_LAUNCHERS:
        return None
    if name in ('msiexec', 'msiexec.exe'):
        executable = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'msiexec.exe'
        arguments = []
        for arg in args[1:]:
            if arg.casefold() in QUIET or re.fullmatch(r'/q[nbrf][+!-]*', arg, re.I):
                continue
            if arg.casefold() == '/i':
                arg = '/x'
            elif re.fullmatch(r'/i\{[0-9a-f-]+\}', arg, re.I):
                arg = '/x' + arg[2:]
            arguments.append(arg)
        if not any(arg.casefold() == '/x' or arg.casefold().startswith('/x{') for arg in arguments):
            return None
    else:
        if not executable.is_absolute() or executable.suffix.casefold() != '.exe':
            return None
        arguments = [arg for arg in args[1:] if arg.casefold() not in QUIET]
    if not executable.is_file():
        return None
    return [str(executable), *arguments]


def shell_execute(executable, arguments):
    from ctypes import wintypes
    invoke = ctypes.windll.shell32.ShellExecuteW
    invoke.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
                       wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]
    invoke.restype = ctypes.c_void_p
    code = invoke(None, 'open', executable, subprocess.list2cmdline(arguments), None, 1)
    if not code or code <= 32:
        raise OSError(f'The system could not open the official removal interface (code {code}).')


class ApplicationCatalog:
    def __init__(self):
        self.lock = threading.RLock()
        self.items = {}
        self.running = False
        self.loaded = False
        self.errors = 0

    def list(self):
        with self.lock:
            if not self.loaded and not self.running:
                self.running = True
                threading.Thread(target=self.discover, daemon=True).start()
            return dict(items=[{k: v for k, v in item.items() if not k.startswith('_')}
                               for item in sorted(self.items.values(), key=lambda item: item['name'].casefold())],
                        running=self.running, errors=self.errors,
                        note='Registry, application bundle, or desktop-entry metadata. Locations are evidence, not complete file ownership.')

    def add(self, key, name, install_path='', version='', publisher='', size=0,
            method='', argv=None, package='', evidence='installation location'):
        identity = hashlib.sha256((sys.platform + ':' + key).encode()).hexdigest()[:24]
        location = os.path.expandvars(str(install_path)).strip(' "')
        if location and not Path(location).is_absolute():
            location = ''
        item = dict(id=identity, name=str(name), version=str(version), publisher=str(publisher),
                    installPath=location, size=max(0, int(size)), sizeEstimated=bool(size),
                    method=method, uninstallAvailable=bool(argv), package=package,
                    officialCommand=subprocess.list2cmdline(argv) if argv and sys.platform == 'win32' else shlex.join(argv or []),
                    components=[dict(path=location, kind='installation location', evidence=evidence)] if location else [],
                    _argv=argv)
        with self.lock:
            self.items[identity] = item

    def discover(self):
        try:
            if sys.platform == 'win32':
                self.windows()
            elif sys.platform == 'darwin':
                self.mac()
            else:
                self.linux()
        except (OSError, ValueError, subprocess.SubprocessError):
            with self.lock:
                self.errors += 1
        finally:
            with self.lock:
                self.running = False
                self.loaded = True

    def windows(self):
        import winreg
        uninstall_key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall'
        seen = set()
        for hive_name, hive in [('HKLM', winreg.HKEY_LOCAL_MACHINE), ('HKCU', winreg.HKEY_CURRENT_USER)]:
            for view in [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                try:
                    root = winreg.OpenKey(hive, uninstall_key, 0, winreg.KEY_READ | view)
                except OSError:
                    continue
                with root:
                    for i in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            key = winreg.EnumKey(root, i)
                            with winreg.OpenKey(root, key) as entry:
                                def value(name, default=''):
                                    try:
                                        return winreg.QueryValueEx(entry, name)[0]
                                    except OSError:
                                        return default
                                name = value('DisplayName')
                                if not name or value('SystemComponent', 0) == 1:
                                    continue
                                command = value('UninstallString')  # Never QuietUninstallString.
                                location = value('InstallLocation')
                                version = value('DisplayVersion')
                                signature = (str(name), str(version), str(location), str(command))
                                if signature in seen:
                                    continue
                                seen.add(signature)
                                argv = interactive_windows_command(str(command))
                                method = 'Official uninstaller' if argv else 'Windows Installed Apps'
                                argv = argv or ['ms-settings:appsfeatures']
                                self.add(hive_name + ':' + str(view) + ':' + key, name, location,
                                         version, value('Publisher'), int(value('EstimatedSize', 0) or 0) * 1024,
                                         method, argv, evidence='InstallLocation recorded in the Windows uninstall registry')
                        except (OSError, ValueError, TypeError):
                            self.errors += 1

    def mac(self, directories=None):
        for directory in directories or [Path('/Applications'), Path.home() / 'Applications']:
            if not directory.is_dir():
                continue
            for bundle in directory.glob('*.app'):
                try:
                    with (bundle / 'Contents' / 'Info.plist').open('rb') as stream:
                        info = plistlib.load(stream)
                    self.add(str(bundle), info.get('CFBundleDisplayName') or info.get('CFBundleName') or bundle.stem,
                             bundle, info.get('CFBundleShortVersionString', ''), info.get('CFBundleIdentifier', ''),
                             method='Review application in Finder', argv=['/usr/bin/open', '-R', str(bundle)],
                             evidence='Application bundle containing Contents/Info.plist')
                except (OSError, ValueError, plistlib.InvalidFileException):
                    self.errors += 1

    def linux(self, locations=None):
        locations = locations or [Path.home() / '.local/share/applications', Path('/usr/local/share/applications'),
                     Path('/usr/share/applications'), Path.home() / '.local/share/flatpak/exports/share/applications',
                     Path('/var/lib/flatpak/exports/share/applications')]
        entries, seen = [], set()
        for directory in locations:
            for file in directory.glob('*.desktop'):
                if file.name in seen:
                    continue
                seen.add(file.name)
                config = configparser.ConfigParser(interpolation=None, strict=False)
                try:
                    config.read(file, encoding='utf-8')
                    info = config['Desktop Entry']
                    if info.get('Type') != 'Application' or info.get('Hidden') == 'true' or info.get('NoDisplay') == 'true':
                        continue
                    entries.append((file, dict(info)))
                except (OSError, KeyError, configparser.Error, UnicodeError):
                    self.errors += 1
        packages = {}
        dpkg = shutil.which('dpkg-query')
        if dpkg and entries:
            result = subprocess.run([dpkg, '--search', *[str(p) for p, _ in entries]],
                                    capture_output=True, text=True, timeout=20)
            for line in result.stdout.splitlines():
                if ': ' in line:
                    package, path = line.split(': ', 1)
                    if re.fullmatch(r'[a-zA-Z0-9.+:_-]+', package):
                        packages[path] = package
        terminal = shutil.which('x-terminal-emulator') or shutil.which('xterm')
        for file, info in entries:
            package, command = packages.get(str(file), ''), None
            flatpak = info.get('x-flatpak', '')
            if flatpak and re.fullmatch(r'[A-Za-z0-9._-]+', flatpak) and shutil.which('flatpak'):
                package = flatpak
                command = [shutil.which('flatpak'), 'uninstall', '--user' if str(file).startswith(str(Path.home())) else '--system', package]
            elif package and shutil.which('apt') and shutil.which('sudo'):
                command = [shutil.which('sudo'), shutil.which('apt'), 'remove', '--', package]
            elif shutil.which('rpm') and shutil.which('dnf') and shutil.which('sudo'):
                result = subprocess.run([shutil.which('rpm'), '-qf', '--queryformat', '%{NAME}', str(file)],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and re.fullmatch(r'[A-Za-z0-9.+_-]+', result.stdout):
                    package = result.stdout
                    command = [shutil.which('sudo'), shutil.which('dnf'), 'remove', '--', package]
            argv = [terminal, '-e', *command] if terminal and command else None
            self.add(str(file), info.get('name', file.stem), method='Interactive system package manager',
                     argv=argv, package=package)
            # Exec is intentionally never executed and its paths do not imply ownership.

    def uninstall(self, data):
        if data.get('confirm') is not True:
            raise ValueError('Explicit confirmation is required before opening removal tools.')
        with self.lock:
            item = self.items.get(data.get('id'))
            if not item:
                raise ValueError('Application not found. Refresh the application list.')
            argv = item['_argv']
            if not argv:
                raise ValueError('Use the system package manager to remove this application.')
            argv = list(argv)
        if sys.platform == 'win32':
            shell_execute(argv[0], argv[1:])
        else:
            subprocess.Popen(argv, shell=False)
        return dict(ok=True, launched=True, method=item['method'],
                    note='The system removal interface was opened. Removal is not yet confirmed. Shared components and user data may remain.')

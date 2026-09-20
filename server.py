"""Obsydian Finder: private, local, standard-library file service."""
import argparse
import ctypes
import hashlib
import heapq
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from references import ReferenceIndex
from apps import ApplicationCatalog
from launch import current as current_instance, instance_lock, save_session, version, SESSION

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
APP_VERSION = version()
SYSTEM_NAMES = {'$recycle.bin', 'system volume information', 'windows', 'program files',
                'program files (x86)', 'programdata', 'recovery', '.trash', '.trashes',
                'lost+found', 'proc', 'sys', 'dev'}

def protected(path):
    return any(part.casefold() in SYSTEM_NAMES for part in Path(path).parts)

def linked(path):
    p = Path(path)
    return p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) or bool(
        getattr(p.lstat(), 'st_file_attributes', 0) & 0x400)

class Store:
    def __init__(self):
        self.lock = threading.RLock()
        self.nodes = {}
        self.keys = []
        self.key_set = set()
        self.cancel_event = threading.Event()
        self.started = 0
        self.references = ReferenceIndex(self)
        self.applications = ApplicationCatalog()
        self.state = dict(running=False, root='', roots=[], mode='folder', includeSystem=False,
                          files=0, bytes=0, errors=0, excluded=0, current='', complete=False,
                          cancelled=False, elapsed=0)

    def checked(self, value, must_exist=True, allow_protected=False):
        raw = Path(value)
        if not raw.is_absolute():
            raise ValueError('An absolute path is required.')
        for p in [raw, *raw.parents]:
            if p.exists() or p.is_symlink():
                if linked(p):
                    raise ValueError('Symlinks and junctions are not allowed.')
        p = raw.resolve()
        if not any(p.is_relative_to(Path(root)) for root in self.state['roots']):
            raise ValueError('The path is outside the scanned folders.')
        if protected(p) and not allow_protected:
            raise ValueError('Protected system path: read-only access is available.')
        if must_exist and not p.exists():
            raise ValueError('The path no longer exists. Scan again.')
        return p

    def start(self, value='', all_disks=False, include_system=False):
        with self.lock:
            if self.state['running']:
                raise ValueError('A scan is already running.')
            candidates = [d['path'] for d in drives() if d.get('isDisk')] if all_disks else [value]
            roots, unavailable = [], []
            for value in candidates:
                raw = Path(value)
                if not raw.is_absolute() or not raw.is_dir() or (protected(raw) and not include_system):
                    if all_disks:
                        unavailable.append(str(raw))
                        continue
                    raise ValueError('Select an accessible absolute folder path.')
                for p in [raw, *raw.parents]:
                    if linked(p):
                        raise ValueError('Symlinks and junctions cannot be scanned.')
                root = raw.resolve()
                if not any(root.is_relative_to(Path(r)) for r in roots):
                    roots = [r for r in roots if not Path(r).is_relative_to(root)]
                    roots.append(str(root))
            if not roots:
                raise ValueError('No accessible disks were found.')
            root = '@computer' if all_disks else roots[0]
            self.references.invalidate()
            self.nodes = {}
            self.keys = []
            self.key_set = set()
            self.cancel_event = threading.Event()
            self.started = time.monotonic()
            self.state = dict(running=True, root=root, roots=roots, mode='all' if all_disks else 'folder',
                              includeSystem=bool(include_system), files=0, bytes=0, errors=0,
                              excluded=0, current=root, complete=False, cancelled=False, elapsed=0,
                              unavailableRoots=unavailable)
            self.references.start()
            threading.Thread(target=self.scan, args=(roots,), daemon=True).start()
            return dict(ok=True, root=root, roots=roots)

    def status(self):
        with self.lock:
            state = dict(self.state)
            if state['running']:
                state['elapsed'] = round(time.monotonic() - self.started, 2)
            return state

    def cancel(self):
        with self.lock:
            if self.state['running']:
                self.cancel_event.set()
            self.references.cancel()
            return dict(ok=True, cancelling=self.state['running'])

    def scan(self, roots):
        nodes, dirty, failed, frames = {}, set(), set(), []
        counters = dict(files=0, bytes=0, errors=0, excluded=0, current='')
        last_publish, changes = time.monotonic(), 0
        virtual = self.state['mode'] == 'all'
        include_system = self.state['includeSystem']
        def publish(force=False):
            nonlocal last_publish, changes
            if not force and changes < 100 and time.monotonic() - last_publish < .1:
                return
            with self.lock:
                for key in dirty:
                    if key not in self.nodes:
                        self.keys.append(key)
                        self.key_set.add(key)
                        children = []
                    else:
                        children = self.nodes[key]['children']
                    children.extend(nodes[key]['children'][len(children):])
                    self.nodes[key] = dict(nodes[key], children=children)
                self.state.update(counters)
                self.state['elapsed'] = round(time.monotonic() - self.started, 2)
            dirty.clear()
            last_publish, changes = time.monotonic(), 0

        def incomplete(key):
            while key is not None:
                failed.add(key)
                dirty.add(key)
                key = nodes[key]['parent']

        def enter(p, parent):
            nonlocal changes
            key = str(p)
            counters['current'] = key
            changes += 1
            try:
                if linked(p) or (protected(p) and not include_system):
                    counters['excluded'] += 1
                    return
                stat = p.stat()
                is_dir = p.is_dir()
                if not is_dir and not p.is_file():
                    counters['excluded'] += 1
                    return
                existing = key in nodes
                nodes[key] = dict(name=p.name or key, path=key, size=0 if is_dir else stat.st_size,
                                  isDir=is_dir, ext='' if is_dir else p.suffix.lower(), children=[],
                                  partial=is_dir, readOnly=protected(p), parent=parent)
                dirty.add(key)
                if parent is not None and not existing:
                    nodes[parent]['children'].append(key)
                    dirty.add(parent)
                if is_dir:
                    try:
                        frames.append((key, os.scandir(p)))
                    except OSError:
                        counters['errors'] += 1
                        incomplete(key)
                else:
                    counters['files'] += 1
                    counters['bytes'] += stat.st_size
                    ancestor = parent
                    while ancestor is not None:
                        nodes[ancestor]['size'] += stat.st_size
                        dirty.add(ancestor)
                        ancestor = nodes[ancestor]['parent']
            except OSError:
                counters['errors'] += 1
                if parent is not None:
                    incomplete(parent)
            finally:
                publish()

        try:
            if virtual:
                nodes['@computer'] = dict(name='This computer', path='@computer', size=0, isDir=True,
                                          ext='', children=[], partial=True, readOnly=True, parent=None)
                dirty.add('@computer')
                for root in roots:
                    nodes[root] = dict(name=Path(root).name or root, path=root, size=0, isDir=True,
                                       ext='', children=[], partial=True, readOnly=protected(root),
                                       parent='@computer')
                    nodes['@computer']['children'].append(root)
                    dirty.add(root)
                publish(True)
            for root in roots:
                if self.cancel_event.is_set():
                    break
                enter(Path(root), '@computer' if virtual else None)
                publish(True)
                while frames and not self.cancel_event.is_set():
                    key, entries = frames[-1]
                    try:
                        entry = next(entries)
                    except StopIteration:
                        entries.close()
                        frames.pop()
                        nodes[key]['partial'] = key in failed
                        dirty.add(key)
                        publish()
                        continue
                    except OSError:
                        entries.close()
                        frames.pop()
                        counters['errors'] += 1
                        incomplete(key)
                        publish()
                        continue
                    enter(Path(entry.path), key)
            if virtual and not self.cancel_event.is_set():
                nodes['@computer']['partial'] = '@computer' in failed
                dirty.add('@computer')
        except Exception as exc:
            counters['errors'] += 1
            counters['lastError'] = str(exc)
            self.cancel_event.set()
        finally:
            for _, entries in frames:
                entries.close()
            publish(True)
            with self.lock:
                self.state['cancelled'] = self.cancel_event.is_set()
                self.state['complete'] = not self.state['cancelled']
                self.state['running'] = False
                self.state['current'] = ''
                self.state['elapsed'] = round(time.monotonic() - self.started, 2)

    @staticmethod
    def public(node):
        return {k: v for k, v in node.items() if k not in ('children', 'parent')}

    def search(self, query):
        query = query.casefold()
        if not query:
            return dict(items=[], count=0)
        with self.lock:
            nodes, keys, length = self.nodes, self.keys, len(self.keys)
        heap, count = [], 0
        for offset in range(0, length, 500):
            with self.lock:
                batch = [nodes[key] for key in keys[offset:min(length, offset + 500)] if key in nodes]
            for node in batch:
                if query in node['name'].casefold():
                    count += 1
                    entry = (node['size'], node['path'], node)
                    if len(heap) < 500:
                        heapq.heappush(heap, entry)
                    elif entry[:2] > heap[0][:2]:
                        heapq.heapreplace(heap, entry)
        return dict(items=[self.public(entry[2]) for entry in sorted(heap, reverse=True)], count=count)

    def children(self, value):
        with self.lock:
            return self._children(value)

    def previews(self, value):
        with self.lock:
            path = '@computer' if value == '@computer' and self.state['mode'] == 'all' else str(self.checked(value, allow_protected=True))
            parent = self.nodes.get(path)
            if not parent or not parent['isDir']:
                raise ValueError('This folder is not available. Wait for the scan or scan again.')
            directories = heapq.nsmallest(20, (self.nodes[c] for c in parent['children']
                                               if c in self.nodes and self.nodes[c]['isDir']),
                                          key=lambda n: (-n['size'], n['name'].casefold()))
            result = {}
            for directory in directories:
                node = self.nodes[directory['path']]
                top = heapq.nsmallest(8, (self.nodes[c] for c in node['children'] if c in self.nodes),
                                     key=lambda n: (-n['size'], n['name'].casefold()))
                result[directory['path']] = dict(items=[self.public(n) for n in top],
                                               count=len(node['children']), partial=node['partial'])
            return dict(path=path, previews=result)

    def _children(self, value):
        path = '@computer' if value == '@computer' and self.state['mode'] == 'all' else str(self.checked(value, allow_protected=True))
        node = self.nodes.get(path)
        if not node or not node['isDir']:
            raise ValueError('This folder is not available. Wait for the scan or scan again.')
        count = len(node['children'])
        items = heapq.nsmallest(1000, (self.nodes[c] for c in node['children'] if c in self.nodes),
                               key=lambda n: (-n['size'], n['name'].casefold()))
        if not self.state['running']:
            missing = []
            for item in items:
                try:
                    Path(item['path']).lstat()
                except FileNotFoundError:
                    if item['path'] not in self.state['roots']:
                        missing.append(item['path'])
                except OSError:
                    pass
            if missing:
                self.references.invalidate()
                for key in missing:
                    self._prune(key)
                self.references.start()
                items = [item for item in items if item['path'] not in missing]
                count = len(node['children'])
        return dict(path=path, parent=node['parent'],
                    items=[self.public(n) for n in items], total=node['size'], count=count, partial=node['partial'])

    def duplicates(self, value):
        with self.lock:
            if not self.state['complete']:
                raise ValueError('Complete a scan before checking duplicates.')
            return self._duplicates(value)

    def _duplicates(self, value):
        selected = self.checked(value)
        node = self.nodes.get(str(selected))
        if not node or node['isDir']:
            raise ValueError('Select a scanned file.')
        def digest(p):
            self.checked(str(p))
            with open(p, 'rb') as stream:
                h = hashlib.sha256()
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    h.update(chunk)
                return h.hexdigest()
        before = selected.stat()
        target = digest(selected)
        items, errors = [], 0
        for n in list(self.nodes.values()):
            if n['isDir'] or n['size'] != before.st_size or n['path'] == str(selected):
                continue
            try:
                p = self.checked(n['path'])
                first = p.stat()
                candidate = digest(p)
                after = p.stat()
                if candidate == target and (first.st_size, first.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
                    items.append(self.public(n))
            except (OSError, ValueError):
                errors += 1
        after = selected.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('The file changed during comparison. Try again.')
        return dict(items=items, count=len(items), errors=errors, algorithm='SHA-256')

    def action(self, data):
        with self.lock:
            return self._action(data)

    def _subtree(self, key):
        pending, found = [key], []
        while pending:
            current = pending.pop()
            node = self.nodes.get(current)
            if node:
                found.append(current)
                pending.extend(node['children'])
        return found

    def _adjust(self, key, amount):
        while key is not None and key in self.nodes:
            self.nodes[key]['size'] = max(0, self.nodes[key]['size'] + amount)
            key = self.nodes[key]['parent']

    def _prune(self, key):
        node = self.nodes.get(key)
        if not node:
            return
        parent, size = node['parent'], node['size']
        removed = self._subtree(key)
        files = sum(not self.nodes[p]['isDir'] for p in removed)
        if parent in self.nodes:
            self.nodes[parent]['children'] = [p for p in self.nodes[parent]['children'] if p != key]
        self._adjust(parent, -size)
        for p in removed:
            del self.nodes[p]
        self.state['files'] = max(0, self.state['files'] - files)
        self.state['bytes'] = max(0, self.state['bytes'] - size)

    def _relocate(self, source, destination):
        key, new_key = str(source), str(destination)
        node = self.nodes[key]
        old_parent, parent, size = node['parent'], str(destination.parent), node['size']
        subtree = self._subtree(key)
        mapping = {p: str(destination / Path(p).relative_to(source)) for p in subtree}
        moved = {}
        for p in subtree:
            old = self.nodes[p]
            moved[mapping[p]] = dict(old, path=mapping[p],
                                    name=destination.name if p == key else old['name'],
                                    ext=destination.suffix.lower() if p == key and not old['isDir'] else old['ext'],
                                    parent=parent if p == key else mapping[old['parent']],
                                    children=[mapping[c] for c in old['children'] if c in mapping])
        self.nodes[old_parent]['children'] = [p for p in self.nodes[old_parent]['children'] if p != key]
        self._adjust(old_parent, -size)
        for p in subtree:
            del self.nodes[p]
        self.nodes.update(moved)
        for moved_key in moved:
            if moved_key not in self.key_set:
                self.keys.append(moved_key)
                self.key_set.add(moved_key)
        self.nodes[parent]['children'].append(new_key)
        self._adjust(parent, size)

    def actions(self, data):
        if data.get('action') != 'trash':
            raise ValueError('Only recycle operations support multiple selection.')
        paths = data.get('paths')
        if not isinstance(paths, list) or not 1 <= len(paths) <= 200 or not all(isinstance(p, str) for p in paths):
            raise ValueError('Select between 1 and 200 file or folder paths.')
        with self.lock:
            if self.state['running']:
                raise ValueError('Stop the scan and wait for it to finish before modifying files.')
            self.references.invalidate()
            results = []
            for value in paths:
                try:
                    p = self.checked(value, must_exist=False)
                    if str(p) in self.state['roots']:
                        raise ValueError('The scan root cannot be modified.')
                    try:
                        p.lstat()
                    except FileNotFoundError:
                        self._prune(str(p))
                        results.append(dict(path=value, ok=True, missing=True))
                        continue
                    if str(p) not in self.nodes:
                        raise ValueError('This item is not in the current scan.')
                    recycle(p)
                    self._prune(str(p))
                    results.append(dict(path=value, ok=True, missing=False))
                except (ValueError, OSError) as exc:
                    results.append(dict(path=value, ok=False, missing=False, error=str(exc)))
            self.references.start()
            return dict(results=results, files=self.state['files'], bytes=self.state['bytes'])

    def _action(self, data):
        if self.state['running']:
            raise ValueError('Stop the scan and wait for it to finish before modifying files.')
        if data.get('action') == 'trash':
            result = self.actions(dict(action='trash', paths=[data.get('path', '')]))['results'][0]
            if not result['ok']:
                raise ValueError(result['error'])
            return dict(result, rescanning=False)
        p = self.checked(data.get('path', ''))
        action = data.get('action')
        if action == 'open':
            if sys.platform == 'win32':
                subprocess.Popen(['explorer.exe', str(p)] if p.is_dir() else ['explorer.exe', '/select,', str(p)])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-R', str(p)])
            else:
                subprocess.Popen(['xdg-open', str(p if p.is_dir() else p.parent)])
            return dict(ok=True)
        if str(p) in self.state['roots']:
            raise ValueError('The scan root cannot be modified.')
        if action in ('move', 'rename'):
            if action == 'rename':
                name = data.get('name', '')
                if not name or name in ('.', '..') or any(c in name for c in '/\\:') or name.endswith(('.', ' ')):
                    raise ValueError('Invalid file name.')
                dest = self.checked(str(p.with_name(name)), False)
            else:
                folder = self.checked(data.get('destination', ''))
                if not folder.is_dir():
                    raise ValueError('The destination must be a folder.')
                dest = self.checked(str(folder / p.name), False)
            if dest.exists() or dest.is_symlink():
                raise ValueError('An item with this name already exists.')
            if p.is_dir() and dest.is_relative_to(p):
                raise ValueError('A folder cannot be moved into itself.')
            if str(p) not in self.nodes or str(dest.parent) not in self.nodes:
                raise ValueError('Both the source and destination folder must be in the current scan.')
            self.references.invalidate()
            # Windows rename refuses overwrite; on POSIX reserve destination first.
            if sys.platform != 'win32':
                if p.is_dir():
                    dest.mkdir()
                else:
                    dest.touch(exist_ok=False)
                try:
                    os.rename(p, dest)
                except Exception:
                    if dest.is_dir():
                        dest.rmdir()
                    else:
                        dest.unlink()
                    raise
            else:
                os.rename(p, dest)
        else:
            raise ValueError('Unknown action.')
        self._relocate(p, dest)
        self.references.start()
        return dict(ok=True, path=str(dest), rescanning=False)

def recycle(p):
    if sys.platform == 'win32':
        from windows_recycle import recycle as windows_recycle
        windows_recycle(p)
    elif sys.platform == 'darwin':
        trash = Path.home() / '.Trash'
        if not trash.is_dir() or linked(trash):
            raise ValueError('The Trash is unavailable.')
        dest = trash / (p.name + '-' + secrets.token_hex(6))
        os.rename(p, dest)
    else:
        # gio follows the desktop trash implementation, including mount-specific trash.
        gio = shutil.which('gio')
        if not gio:
            raise ValueError('Desktop Trash is unavailable. Install gio to use this action.')
        result = subprocess.run([gio, 'trash', '--', str(p)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('Trash is unavailable for this path.')

def drives():
    paths = []
    if sys.platform == 'win32':
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        paths = [f'{chr(65+i)}:\\' for i in range(26) if mask & (1 << i)]
    elif sys.platform == 'darwin':
        paths = ['/'] + [str(p) for p in Path('/Volumes').iterdir() if p.is_dir()]
    else:
        paths = ['/']
        try:
            for line in Path('/proc/mounts').read_text().splitlines():
                mount = line.split()[1].replace('\\040', ' ')
                if mount.startswith(('/media/', '/mnt/', '/run/media/')):
                    paths.append(mount)
        except OSError:
            pass
    result = []
    for p in dict.fromkeys(paths + [str(Path.home())]):
        try:
            usage = shutil.disk_usage(p)
            result.append(dict(path=p, label='Home folder' if p == str(Path.home()) else p,
                               total=usage.total, free=usage.free, isDisk=p in paths))
        except OSError:
            pass
    return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        host = self.headers.get('Host', '')
        expected = f'127.0.0.1:{self.server.server_port}'
        alternate = f'localhost:{self.server.server_port}'
        if host not in (expected, alternate):
            return self.reply({'error': 'Host is not allowed.'}, 403)
        origin = self.headers.get('Origin')
        if origin and origin not in ('http://' + expected, 'http://' + alternate):
            return self.reply({'error': 'Origin is not allowed.'}, 403)
        url = urllib.parse.urlsplit(self.path)
        if url.path.startswith('/api/'):
            if not secrets.compare_digest(self.headers.get('X-Obsydian-Token', ''), self.server.token):
                return self.reply({'error': 'Unauthorized session. Reload the page.'}, 403)
            try:
                data = {}
                if self.command == 'POST':
                    length = int(self.headers.get('Content-Length', '0'))
                    if length > 16384 or length < 0:
                        raise ValueError('The request is too large.')
                    data = json.loads(self.rfile.read(length) or b'{}')
                    if not isinstance(data, dict):
                        raise ValueError('Invalid request.')
                query = urllib.parse.parse_qs(url.query)
                s = self.server.store
                if self.command == 'GET' and url.path == '/api/drives':
                    result = {'drives': drives()}
                elif self.command == 'GET' and url.path == '/api/status':
                    result = s.status()
                elif self.command == 'GET' and url.path == '/api/children':
                    result = s.children(query.get('path', [s.state['root']])[0])
                elif self.command == 'GET' and url.path == '/api/previews':
                    result = s.previews(query.get('path', [s.state['root']])[0])
                elif self.command == 'GET' and url.path == '/api/applications':
                    result = s.applications.list()
                elif self.command == 'POST' and url.path == '/api/applications/uninstall':
                    result = s.applications.uninstall(data)
                elif self.command == 'GET' and url.path == '/api/references/status':
                    result = s.references.status()
                elif self.command == 'GET' and url.path == '/api/references':
                    result = s.references.query(query.get('path', [s.state['root']])[0])
                elif self.command == 'POST' and url.path == '/api/references/start':
                    result = s.references.start()
                elif self.command == 'POST' and url.path == '/api/references/cancel':
                    result = s.references.cancel()
                elif self.command == 'GET' and url.path == '/api/search':
                    q = query.get('q', [''])[0].casefold()
                    result = s.search(q)
                elif self.command == 'POST' and url.path == '/api/scan':
                    result = s.start(data.get('path', ''), all_disks=data.get('all', False), include_system=data.get('includeSystem', False))
                elif self.command == 'POST' and url.path == '/api/cancel':
                    result = s.cancel()
                elif self.command == 'POST' and url.path == '/api/duplicates':
                    result = s.duplicates(data.get('path', ''))
                elif self.command == 'POST' and url.path == '/api/action':
                    result = s.action(data)
                elif self.command == 'POST' and url.path == '/api/actions':
                    result = s.actions(data)
                elif self.command == 'POST' and url.path == '/api/shutdown':
                    s.cancel()
                    result = dict(ok=True)
                    callback = getattr(self.server, 'desktop_callback', None)
                    if callback:
                        callback('quit')
                    else:
                        threading.Thread(target=self.server.shutdown, daemon=True).start()
                elif self.command == 'POST' and url.path == '/api/desktop':
                    callback = getattr(self.server, 'desktop_callback', None)
                    if not callback or data.get('action') not in ('show', 'tray'):
                        raise ValueError('This action requires the desktop application.')
                    callback(data['action'])
                    result = dict(ok=True)
                elif self.command == 'GET' and url.path == '/api/info':
                    result = dict(app='obsydian-finder', version=APP_VERSION, pid=os.getpid(),
                                  desktop=bool(getattr(self.server, 'desktop_callback', None)),
                                  trayAvailable=getattr(self.server, 'tray_available', False))
                else:
                    return self.reply({'error': 'Endpoint not found.'}, 404)
                return self.reply(result)
            except (ValueError, OSError, TypeError) as exc:
                return self.reply({'error': str(exc)}, 400)
        if self.command != 'GET':
            return self.reply({'error': 'Method not allowed.'}, 405)
        name = 'index.html' if url.path == '/' else url.path.lstrip('/')
        if name not in ('index.html', 'app.js', 'styles.css', 'style.css', 'streaming.css', 'scene.js', 'graph.js', 'i18n.js', 'ui.css', 'controls.js', 'applications.js', 'readable.css', 'desktop.css', 'favicon.svg', 'vendor/three.bundle.js', 'assets/obsydian.png', 'assets/obsydian.svg', 'assets/obsydian.ico'):
            return self.reply({'error': 'File not found.'}, 404)
        try:
            file = BASE / 'static' / name
            if not file.exists():
                file = BASE / name
            body = file.read_bytes().replace(b'__TOKEN__', self.server.token.encode())
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(name)[0] or 'application/octet-stream')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            self.reply({'error': 'Interface files not found.'}, 404)

    do_GET = dispatch
    do_POST = dispatch

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    existing = current_instance()
    if existing:
        if not args.no_browser:
            webbrowser.open(existing['url'])
        return
    instance = instance_lock()
    if instance is None:
        for _ in range(50):
            existing = current_instance()
            if existing:
                if not args.no_browser:
                    webbrowser.open(existing['url'])
                return
            time.sleep(.1)
        raise RuntimeError('Another Obsydian instance is starting. Try again shortly.')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.token = secrets.token_urlsafe(32)
    server.store = Store()
    url = f'http://127.0.0.1:{server.server_port}'
    save_session(server.server_port, server.token)
    print('Obsydian Finder: ' + url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.store.cancel()
        server.server_close()
        try:
            data = json.loads(SESSION.read_text(encoding='utf-8'))
            if data.get('pid') == os.getpid():
                SESSION.unlink()
        except (OSError, ValueError):
            pass
        instance.close()

if __name__ == '__main__':
    main()


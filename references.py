"""Bounded streaming static path indexing. Never executes file contents."""
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import unquote

EXTENSIONS = {'.md', '.markdown', '.html', '.htm', '.css', '.scss', '.js', '.jsx', '.mjs',
              '.cjs', '.ts', '.tsx', '.py', '.json', '.yaml', '.yml', '.toml', '.ini',
              '.xml', '.csproj', '.sln', '.props', '.targets', '.vue', '.svelte', '.txt',
              '.cfg', '.conf', '.c', '.h', '.cpp', '.hpp', '.cs', '.rs', '.go', '.sh'}
QUOTED = re.compile(r'''["']([^"'\r\n]{1,1024})["']''')
MARKDOWN = re.compile(r'\]\(\s*<?([^\s)>]{1,1024})>?')
CSS_URL = re.compile(r'url\(\s*([^\s\)\'\"]{1,1024})\s*\)')
SECRET_PARTS = {'credentials', 'secrets', '.ssh', '.aws', '.gnupg', '.azure'}

class ChangedRead(ValueError):
    def __init__(self, count):
        super().__init__('File changed during reference indexing.')
        self.bytes_read = count

def sensitive(path):
    p = Path(path)
    name = p.name.casefold()
    return (any(part.casefold() in SECRET_PARTS for part in p.parts)
            or name.startswith(('.env', 'id_rsa', 'id_ed25519', 'credentials', 'secrets'))
            or p.stem.casefold() in {'key', 'keys', 'token', 'tokens', 'password', 'passwords'}
            or p.suffix.casefold() in {'.pem', '.key', '.pfx', '.p12', '.kdbx'})

class ReferenceIndex:
    MAX_FILE = 1024 * 1024
    MAX_BYTES = 64 * 1024 * 1024
    MAX_FILES = 20000
    MAX_EDGES = 50000
    MAX_PENDING = 50000
    BATCH = 256

    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.job = None
        self.event = threading.Event()
        self.edges = []
        self.state = self.empty()

    @staticmethod
    def empty():
        return dict(running=False, complete=False, cancelled=False, stale=False,
                    files=0, bytes=0, edges=0, skipped=0, limited=False, errors=0,
                    current='', elapsed=0, maxFileBytes=1024*1024,
                    maxBytes=64*1024*1024, maxFiles=20000)

    def invalidate(self):
        with self.lock:
            self.event.set()
            self.job = None
            self.edges = []
            self.state = dict(self.empty(), stale=True)

    def status(self):
        with self.lock:
            return dict(self.state)

    def cancel(self):
        with self.lock:
            self.event.set()
            return dict(ok=True, cancelling=self.state['running'])

    def start(self):
        with self.store.lock:
            if not self.store.state['root']:
                raise ValueError('Start a file scan before indexing references.')
            nodes, keys = self.store.nodes, self.store.keys
            roots = tuple(self.store.state['roots'])
            with self.lock:
                if self.state['running']:
                    return dict(ok=True, running=True)
                self.job = job = object()
                self.event = event = threading.Event()
                self.edges = []
                self.state = dict(self.empty(), running=True)
                threading.Thread(target=self.run, args=(job, event, nodes, keys, roots), daemon=True).start()
                return dict(ok=True, running=True)

    def read(self, path, remaining):
        # Validate all components through the same no-link policy as file actions.
        self.store.checked(str(path), allow_protected=True)
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            if os.name == 'nt':
                import ctypes
                import msvcrt
                from ctypes import wintypes
                function = ctypes.windll.kernel32.GetFinalPathNameByHandleW
                function.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
                function.restype = wintypes.DWORD
                buffer = ctypes.create_unicode_buffer(32768)
                size = function(msvcrt.get_osfhandle(stream.fileno()), buffer, len(buffer), 0)
                final = buffer.value
                if final.startswith('\\\\?\\UNC\\'):
                    final = '\\\\' + final[8:]
                elif final.startswith('\\\\?\\'):
                    final = final[4:]
                if not size or size >= len(buffer) or os.path.normcase(final) != os.path.normcase(str(path)):
                    raise ValueError('File location changed while opening it.')
            before = os.fstat(stream.fileno())
            if before.st_size > min(self.MAX_FILE, remaining):
                return None
            content = stream.read(min(self.MAX_FILE, remaining))
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ChangedRead(len(content))
            return content if len(content) <= self.MAX_FILE else None

    def candidates(self, source, literal, roots):
        literal = unquote(literal.strip()).replace('\\\\', '\\')
        if not literal or len(literal) > 1024 or any(ord(c) < 32 for c in literal):
            return []
        if '://' in literal or literal.startswith(('data:', 'mailto:', '#', '//')):
            return []
        literal = literal.split('#', 1)[0].split('?', 1)[0]
        if not any(c in literal for c in ('/', '\\', '.')):
            return []
        raw = Path(literal)
        base = raw if raw.is_absolute() else Path(source).parent / raw
        # Lexical normalization only: reference resolution must not touch external paths.
        base = Path(os.path.abspath(base))
        if not any(base.is_relative_to(Path(root)) for root in roots) or sensitive(base):
            return []
        candidates = [base]
        if not base.suffix:
            candidates += [Path(str(base) + ext) for ext in ('.js', '.ts', '.tsx', '.jsx', '.json', '.py')]
            candidates += [base / ('index' + ext) for ext in ('.js', '.ts', '.tsx', '.jsx')]
        return [str(candidate) for candidate in candidates if str(candidate) != source]

    def resolve(self, source, literal, nodes, roots):
        for key in self.candidates(source, literal, roots):
            if key in nodes and not nodes[key]['isDir'] and key != source:
                return key
        return None

    def run(self, job, event, nodes, keys, roots):
        state = dict(self.empty(), running=True)
        started = last = time.monotonic()
        outgoing, seen, waiting, attempted = [], set(), {}, set()
        unresolved, next_record, cursor = {}, 0, 0
        source_partial = False
        def publish(force=False):
            nonlocal last
            if not force and time.monotonic() - last < .1 and len(outgoing) < 100:
                return
            state['elapsed'] = round(time.monotonic() - started, 2)
            with self.lock:
                if self.job is job:
                    self.edges.extend(outgoing)
                    self.state = dict(state)
            outgoing.clear()
            last = time.monotonic()

        def add_edge(source, target, evidence):
            pair = (source, target)
            if pair in seen:
                return
            if len(seen) >= self.MAX_EDGES:
                state['limited'] = True
                return
            seen.add(pair)
            outgoing.append(dict(source=source, target=target, kind='reference',
                                 evidence=evidence, confidence='resolved'))
            state['edges'] += 1

        def target_available(key, node):
            if node['isDir']:
                return
            for record_id in waiting.pop(key, ()):
                record = unresolved.pop(record_id, None)
                if record is None:
                    continue
                source, evidence, candidates = record
                for candidate in candidates:
                    bucket = waiting.get(candidate)
                    if bucket is not None:
                        bucket.discard(record_id)
                        if not bucket:
                            del waiting[candidate]
                add_edge(source, key, evidence)

        def record_reference(source, literal, number):
            nonlocal next_record
            candidates = self.candidates(source, literal, roots)
            if not candidates:
                return
            evidence = f'line {number}: {literal[:160]}'
            with self.store.lock:
                target = next((key for key in candidates if key in nodes and not nodes[key]['isDir']), None)
            if target:
                add_edge(source, target, evidence)
            elif len(unresolved) < self.MAX_PENDING and len(seen) < self.MAX_EDGES:
                next_record += 1
                unresolved[next_record] = (source, evidence, candidates)
                for candidate in candidates:
                    waiting.setdefault(candidate, set()).add(next_record)
            else:
                state['limited'] = True

        def process_source(source, node):
            if node['isDir'] or source in attempted:
                return
            if sensitive(source) or Path(source).suffix.casefold() not in EXTENSIONS or node['size'] > self.MAX_FILE:
                state['skipped'] += 1
                return
            if state['files'] >= self.MAX_FILES or state['bytes'] + node['size'] > self.MAX_BYTES:
                state['limited'] = True
                state['skipped'] += 1
                return
            state['current'] = source
            attempted.add(source)
            state['files'] += 1
            try:
                content = self.read(Path(source), self.MAX_BYTES - state['bytes'])
                if event.is_set():
                    return
                if content is not None:
                    state['bytes'] += len(content)
                if content is None or b'\x00' in content:
                    state['skipped'] += 1
                    return
                text = content.decode('utf-8-sig', errors='replace')
                for number, line in enumerate(text.splitlines(), 1):
                    if event.is_set():
                        break
                    for pattern in (QUOTED, MARKDOWN, CSS_URL):
                        for match in pattern.finditer(line):
                            if event.is_set():
                                return
                            record_reference(source, match.group(1), number)
            except (OSError, ValueError) as exc:
                state['bytes'] += getattr(exc, 'bytes_read', 0)
                state['errors'] += 1

        try:
            while not event.is_set():
                with self.store.lock:
                    if self.store.nodes is not nodes or self.store.keys is not keys:
                        event.set()
                        break
                    batch_keys = keys[cursor:cursor + self.BATCH]
                    cursor += len(batch_keys)
                    batch = [(key, nodes[key]) for key in batch_keys if key in nodes]
                    scanning = self.store.state['running']
                    source_partial = self.store.state['cancelled']
                for source, node in batch:
                    if event.is_set():
                        break
                    target_available(source, node)
                    process_source(source, node)
                    publish()
                if not batch_keys:
                    if not scanning:
                        break
                    publish()
                    event.wait(.08)
        except Exception:
            state['errors'] += 1
            event.set()
        finally:
            cancelled = event.is_set() or source_partial
            state.update(running=False, complete=not cancelled, cancelled=cancelled, current='')
            publish(True)

    def query(self, value):
        with self.store.lock:
            if value == '@computer' and self.store.state['mode'] == 'all':
                path, directory = value, True
            else:
                path = str(self.store.checked(value, allow_protected=True))
                node = self.store.nodes.get(path)
                if node is None:
                    raise ValueError('This path is not in the current scan.')
                directory = node['isDir']
        with self.lock:
            snapshot = list(self.edges)
        def belongs(endpoint):
            return path == '@computer' or endpoint == path or (directory and Path(endpoint).is_relative_to(Path(path)))
        found = [edge for edge in snapshot if belongs(edge['source']) or belongs(edge['target'])]
        return dict(path=path, edges=found[:2000], count=len(found), limited=len(found) > 2000)

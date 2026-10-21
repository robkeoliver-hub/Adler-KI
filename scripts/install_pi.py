#!/usr/bin/env python3
"""Pinned, side-by-side Debian Bookworm installer. No portal/Nginx edits."""
import argparse
import configparser
import hashlib
import io
import json
import os
import platform
import pwd
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

COMMIT = '8a6913eb8f666eb00c0d31c171dd50179884b49d'  # reviewed PR #4; includes #1–#3
MANIFEST_HASH = '48e21a39fdaebdad99ebe3a6ee35d9cc34c3b1ab7aa339ae5e4014b43435fbf0'
SOURCE_URL = 'https://codeload.github.com/robkeoliver-hub/Adler-KI/zip/' + COMMIT
UNIT = 'ki-adler-next.service'
MARKER = '# KI-Adler pinned installer v1\n'
MAX_ARCHIVE = 12 * 1024 * 1024


class InstallError(Exception):
    pass


def private_write(path, data):
    if path.is_symlink():
        raise InstallError('Unsicherer lokaler Dateipfad')
    raw = data.encode() if isinstance(data, str) else data
    fd, temporary = tempfile.mkstemp(prefix='.private-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(raw);file.flush();os.fsync(file.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)



def checked_payload(archive_bytes):
    """Exact independently pinned manifest, no unlisted files or ZIP links."""
    if len(archive_bytes) > MAX_ARCHIVE:
        raise InstallError('Quellarchiv zu groß')
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            entries = archive.infolist()
            if len(entries) > 500 or sum(e.file_size for e in entries) > MAX_ARCHIVE:
                raise InstallError('Quellarchiv überschreitet Limits')
            files = {}
            roots = set()
            for entry in entries:
                parts = PurePosixPath(entry.filename).parts
                if (not parts or entry.filename.startswith('/') or '\\' in entry.filename or ':' in entry.filename
                        or '..' in parts or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
                    raise InstallError('Unsicheres Quellarchiv')
                roots.add(parts[0])
                if entry.is_dir():
                    continue
                relative = '/'.join(parts[1:])
                if not relative or relative in files or entry.file_size > 2 * 1024 * 1024:
                    raise InstallError('Mehrdeutiges Quellarchiv')
                with archive.open(entry) as source:
                    files[relative] = source.read(2 * 1024 * 1024 + 1)
            if len(roots) != 1:
                raise InstallError('Mehrdeutige Archivwurzel')
    except (zipfile.BadZipFile, RuntimeError, UnicodeError):
        raise InstallError('Quellarchiv nicht lesbar') from None
    manifest = files.get('SHA256SUMS', b'')
    if hashlib.sha256(manifest).hexdigest() != MANIFEST_HASH:
        raise InstallError('Quellstand stimmt nicht mit dem geprüften Commit überein')
    expected = {}
    for line in manifest.decode('utf-8').splitlines():
        if '  ' not in line:raise InstallError('Ungültiges Manifest')
        digest, name = line.split('  ', 1)
        if not re.fullmatch('[0-9a-f]{64}', digest) or name in expected:
            raise InstallError('Ungültiges Manifest')
        expected[name] = digest
    if set(files) != set(expected) | {'SHA256SUMS'}:
        raise InstallError('Nicht freigegebene oder fehlende Quelldateien')
    for name, digest in expected.items():
        if hashlib.sha256(files[name]).hexdigest() != digest:
            raise InstallError('Quelldatei-Prüfsumme stimmt nicht')
    return files


def unit_text(release, port, candidate_env):
    if port not in (5057, 5059):
        raise InstallError('Nur freigegebene KI-Ports erlaubt')
    for path in (release, candidate_env):
        if not path.is_absolute() or re.search(r'[\s%"\\]', str(path)):
            raise InstallError('Nicht unterstützter Installationspfad')
    envfile = 'EnvironmentFile=' + str(candidate_env) + '\n' if port == 5059 else ''
    return MARKER + f'''[Unit]
Description=KI-Adler next (isolated demo, pinned {COMMIT[:12]})
After=network.target
[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory={release}
ExecStart={release}/.venv/bin/python {release}/run.py
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=ADLER_MODE=demo
Environment=ADLER_HOST=127.0.0.1
Environment=ADLER_PORT={port}
Environment=ADLER_PROVIDER=mock
Environment=ADLER_EXTERNAL_APPROVED=false
{envfile}Restart=on-failure
RestartSec=5
TimeoutStopSec=20
KillMode=control-group
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
RestrictSUIDSGID=true
[Install]
WantedBy=multi-user.target
'''


def port_open(port):
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def discover_old(old):
    result = subprocess.run(['ss', '-ltnp', 'sport = :5057'], capture_output=True, check=True)
    pids = set(re.findall(rb'pid=(\d+)', result.stdout))
    if len(pids) != 1:
        raise InstallError('Port 5057 kann keinem eindeutigen eigenen Altprozess zugeordnet werden')
    pid = int(pids.pop())
    proc = Path('/proc') / str(pid)
    if proc.stat().st_uid != os.getuid() or (proc / 'cwd').resolve() != old.resolve():
        raise InstallError('Altprozess gehört nicht zur erwarteten Testinstallation')
    argv = (proc / 'cmdline').read_bytes().split(b'\0')
    argv = [os.fsdecode(a) for a in argv if a]
    if len(argv) != 2 or Path(argv[1]).name != 'run.py':
        raise InstallError('Unbekannte Altprozess-Startparameter; keine automatische Ablösung')
    script = Path(argv[1])
    if not script.is_absolute():script = old / script
    if script.resolve() != (old / 'run.py').resolve() or not (old / 'run.py').is_file() or not (old / '.venv/bin/python').is_file():
        raise InstallError('Altprozess lässt sich nicht aus der unveränderten Testinstallation wiederherstellen')
    executable = Path(argv[0])
    if not executable.is_absolute():
        executable = old / executable
    if executable.resolve() != (old / '.venv/bin/python').resolve():
        raise InstallError('Unerwarteter Python-Startpfad')
    for line in (proc / 'cgroup').read_text().splitlines():
        if line.rsplit('/', 1)[-1].endswith('.service'):
            raise InstallError('Altprozess wird bereits durch einen anderen Dienst verwaltet')
    start = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
    # Necessary only for faithful local rollback; never print or publish these values.
    env = {}
    for value in (proc / 'environ').read_bytes().split(b'\0'):
        if b'=' in value:
            key, val = value.split(b'=', 1)
            env[os.fsdecode(key)] = os.fsdecode(val)
    return {'pid': pid, 'start': start, 'argv': argv, 'env': env}


def merged_config(path, old_env):
    cfg = configparser.ConfigParser(interpolation=None)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise InstallError('Unsicherer Konfigurationspfad')
        with path.open(encoding='utf-8') as file:
            cfg.read_file(file)
    if not cfg.has_section('adler'):
        cfg.add_section('adler')
    for name in ('DEMO_CODE', 'PUBLIC_ORIGIN', 'PROVIDER', 'ENDPOINT', 'MODEL', 'API_KEY', 'EXTERNAL_APPROVED'):
        if 'ADLER_' + name in old_env:
            cfg['adler'][name.lower()] = old_env['ADLER_' + name]
    code = cfg['adler'].get('demo_code', '')
    origin = cfg['adler'].get('public_origin', '')
    parsed = urllib.parse.urlsplit(origin)
    if (len(code) < 16 or not code.isascii() or code == 'HIER_EIGENEN_LANGEN_ZUFALLSCODE_EINTRAGEN'
            or parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise InstallError('Bestehende Konfiguration ist nicht vollständig kompatibel; keine Änderung vorgenommen')
    if parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1'):
        raise InstallError('Nicht-lokale Origin benötigt HTTPS')
    output = io.StringIO();cfg.write(output)
    return output.getvalue(), origin


def backup_old(old, target, launch, config_text):
    """Code/config backup only, original venv remains untouched for rollback."""
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as output, tarfile.open(fileobj=output, mode='w:gz') as archive:
        for current, dirs, names in os.walk(old, followlinks=False):
            dirs[:] = [d for d in dirs if d not in ('.venv', 'venv', '.git', '__pycache__', '.pytest_cache')]
            for name in dirs + names:
                path = Path(current) / name
                if path.is_symlink():
                    raise InstallError('Backup wegen symbolischem Link abgebrochen')
                if path.is_file():
                    archive.add(path, arcname='old-code/' + str(path.relative_to(old)), recursive=False)
        for name, content in [('rollback-launch.json', json.dumps(launch)), ('effective-config.ini', config_text)]:
            raw = content.encode();info = tarfile.TarInfo(name);info.size = len(raw);info.mode = 0o600
            archive.addfile(info, io.BytesIO(raw))
    with tarfile.open(target, 'r:gz') as archive:
        if not {'rollback-launch.json', 'effective-config.ini'} <= set(archive.getnames()):
            raise InstallError('Backupprüfung fehlgeschlagen')


def health(port, origin, demo_code=None):
    parsed = urllib.parse.urlsplit(origin)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    cookie = ''
    base = 'http://127.0.0.1:' + str(port) + '/demo/ki-adler/'
    def request(path, data=None, csrf=''):
        nonlocal cookie
        headers = {'Host': parsed.netloc, 'Origin': origin, 'Content-Type': 'application/json', 'X-CSRF-Token': csrf}
        if cookie:headers['Cookie'] = cookie
        req = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            response = opener.open(req, timeout=4)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            from http.cookies import SimpleCookie
            values = SimpleCookie();values.load(response.headers.get('Set-Cookie', ''))
            if values:cookie = '; '.join(name+'='+m.value for name,m in values.items())
            raw = response.read(65536)
            return response.status, raw
    if request('')[0] != 200 or request('api/session')[0] != 401:
        raise InstallError('HTTP-Basisprüfung fehlgeschlagen')
    if demo_code:
        status, raw = request('api/login', {'code': demo_code})
        if status != 200:
            raise InstallError('Synthetischer Testlogin fehlgeschlagen')
        info = json.loads(raw)
        if info.get('mode') != 'mock':
            raise InstallError('Testprovider ist nicht Mock; keine weiteren Anfragen')
        csrf = info['csrf']
        if request('api/chat', {'message': 'Hallo'}, 'wrong')[0] != 403:
            raise InstallError('CSRF-Prüfung fehlgeschlagen')
        status, raw = request('api/chat', {'message': 'Hallo'}, csrf)
        if status != 200 or json.loads(raw).get('synthetic') is not True:
            raise InstallError('Synthetischer Chattest fehlgeschlagen')
        if request('api/logout', {}, csrf)[0] != 200 or request('api/session')[0] != 401:
            raise InstallError('Logoutprüfung fehlgeschlagen')


def public_probe(origin, require_companion=False):
    # Public page only, no cookie, access code or member request.
    url = origin + '/demo/ki-adler/?installcheck=' + COMMIT[:12]
    with urllib.request.urlopen(url, timeout=12) as response:
        body = response.read(200000)
        if response.status != 200 or (require_companion and b'data-adler-shell' not in body):
            raise InstallError('Öffentlicher KI-Proxy bestätigt die neue Oberfläche nicht')


class Installer:
    def __init__(self, home):
        self.home = home
        self.old = home / 'ki-adler-test'
        self.root = home / 'ki-adler'
        self.unit = Path('/etc/systemd/system') / UNIT
        self.log = None

    def run(self, args, label, timeout=180, cwd=None):
        try:
            result = subprocess.run(args, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, cwd=cwd)
            if self.log:
                with self.log.open('ab') as file:
                    file.write(result.stdout)
            if result.returncode:
                raise InstallError(label + ' fehlgeschlagen; Details nur im privaten Installationslog')
            return result.stdout
        except subprocess.TimeoutExpired:
            raise InstallError(label + ' hat das Zeitlimit überschritten') from None

    def write_unit(self, release, port):
        expected_prefix = MARKER
        if self.unit.exists() and (self.unit.is_symlink() or not self.unit.read_text().startswith(expected_prefix)):
            raise InstallError('Vorhandener fremder Dienst wird nicht überschrieben')
        text = unit_text(release, port, self.root / 'private/candidate.env')
        temp = self.root / 'private/next.service'
        private_write(temp, text)
        self.run(['sudo', '-n', 'install', '-m', '644', str(temp), str(self.unit)], 'Eigener Dienst')
        self.run(['sudo', '-n', 'systemctl', 'daemon-reload'], 'Dienstkonfiguration')

    def verify_listener(self, port):
        raw = self.run(['systemctl', 'show', UNIT, '--property=MainPID', '--value'], 'Dienst-PID')
        pid = raw.strip()
        sockets = subprocess.run(['ss', '-ltnp', 'sport = :' + str(port)], capture_output=True, check=True)
        if not pid.isdigit() or pid == b'0' or set(re.findall(rb'pid=(\d+)', sockets.stdout)) != {pid}:
            raise InstallError('Port gehört nicht eindeutig zum neuen Dienst')

    def wait_health(self, port, origin, code=None):
        for _ in range(30):
            try:
                health(port, origin, code)
                return
            except (InstallError, OSError, ValueError):
                time.sleep(0.5)
        raise InstallError('Neue Version wird nicht gesund; bestehendes Portal bleibt unberührt')

    def load_state(self):
        path = self.root / 'private/state.json'
        if self.root.is_symlink() or path.parent.is_symlink() or path.is_symlink():
            raise InstallError('Unsicherer Statuspfad')
        state = json.loads(path.read_text())
        release = self.root / 'releases' / COMMIT
        if state.get('commit') != COMMIT or state.get('release') != str(release) or state.get('port') not in (5057,5059):
            raise InstallError('Ungültiger Installationsstatus')
        if self.unit.is_symlink() or not self.unit.exists() or self.unit.read_text() != unit_text(release, state['port'], self.root / 'private/candidate.env'):
            raise InstallError('Bestehender Dienst stimmt nicht mit Installationsstatus überein')
        self.log = self.root / 'private/install.log'
        if self.log.is_symlink():raise InstallError('Unsicherer Logpfad')
        return state

    def install(self, source_zip=None, config=None):
        if self.root.is_symlink() or not self.old.is_dir() or self.old.is_symlink():
            raise InstallError('Erwartete Verzeichnisse fehlen oder sind verlinkt')
        self.root.mkdir(mode=0o700, exist_ok=True)
        if self.root.stat().st_uid != os.getuid():
            raise InstallError('Installationsordner gehört nicht dem ausführenden Benutzer')
        self.root.chmod(0o700)
        for name in ('private', 'releases', 'backups'):
            path = self.root / name
            if path.is_symlink():
                raise InstallError('Unsicherer Installationspfad')
            path.mkdir(mode=0o700, exist_ok=True);path.chmod(0o700)
        self.log = self.root / 'private/install.log'
        private_write(self.log, b'')
        state_file = self.root / 'private/state.json'
        if state_file.exists():
            state = self.load_state()
            release = Path(state['release'])
            if state['commit'] != COMMIT or release != self.root / 'releases' / COMMIT:
                raise InstallError('Andere Installation vorhanden; kein automatisches Überschreiben')
            if self.unit.is_symlink() or not self.unit.exists() or self.unit.read_text() != unit_text(release, state['port'], self.root / 'private/candidate.env'):
                raise InstallError('Bestehender Dienst stimmt nicht mit Installationsstatus überein')
            self.verify_listener(state['port'])
            self.wait_health(state['port'], state['origin'])
            print('Diese Version läuft bereits; keine zweite Installation angelegt.')
            return state
        if self.unit.exists() or port_open(5059):
            raise InstallError('Zieldienst oder Port 5059 bereits belegt; keine Ablösung fremder Prozesse')
        if shutil.disk_usage(self.root).free < 700 * 1024 * 1024:
            raise InstallError('Mindestens 700 MiB freier Platz erforderlich')
        launch = discover_old(self.old)
        config_path = config or self.old / 'config.ini'
        config_text, origin = merged_config(config_path, launch['env'])
        health(5057, origin)  # public GET/unauthenticated checks only; no old login used
        backup = self.root / 'backups' / (time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3) + '.tar.gz')
        backup_old(self.old, backup, launch, config_text)
        private_write(self.root / 'private/rollback-launch.json', json.dumps(launch))
        print('Private Sicherung erstellt; bisheriger Prozess bleibt unverändert.')
        if source_zip:
            if source_zip.stat().st_size > MAX_ARCHIVE:
                raise InstallError('Quellarchiv zu groß')
            raw = source_zip.read_bytes()
        else:
            with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
                raw = response.read(MAX_ARCHIVE + 1)
        files = checked_payload(raw)
        release = self.root / 'releases' / COMMIT
        if release.exists():
            raise InstallError('Release-Verzeichnis bereits vorhanden; kein Überschreiben')
        staging = Path(tempfile.mkdtemp(prefix='.staging-', dir=self.root / 'releases'))
        for name, content in files.items():
            target = staging / name;target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(content)
            if name.endswith('.sh'):target.chmod(0o700)
        # Final path before venv creation: no stale activation/console shebangs.
        staging.rename(release)
        self.run([sys.executable, '-m', 'venv', str(release / '.venv')], 'Virtuelle Umgebung')
        self.run([str(release / '.venv/bin/python'), '-m', 'pip', 'install', '-r', str(release / 'requirements-dev.txt')], 'Abhängigkeiten', 1800)
        # No real config.ini exists during tests. Conftest clears ADLER_* env.
        self.run([str(release / '.venv/bin/python'), '-m', 'pytest', '-q', 'tests'], '76 Anwendungstests', 300, cwd=release)
        private_write(release / 'config.ini', config_text)
        candidate_code = secrets.token_urlsafe(24)
        private_write(self.root / 'private/candidate.env', 'ADLER_DEMO_CODE=' + candidate_code + '\n')
        self.run(['sudo', '-v'], 'Freigabe für den eigenen systemd-Dienst')
        try:
            self.write_unit(release, 5059)
            self.run(['sudo', '-n', 'systemctl', 'start', UNIT], 'Kandidat starten')
            self.wait_health(5059, origin, candidate_code)
            self.verify_listener(5059)
        except BaseException:
            subprocess.run(['sudo', '-n', 'systemctl', 'stop', UNIT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            raise
        state = {'commit': COMMIT, 'release': str(release), 'origin': origin, 'port': 5059,
                 'backup': str(backup), 'old_pid': launch['pid'], 'old_start': launch['start']}
        private_write(state_file, json.dumps(state, indent=2))
        print('Neue Version geprüft und separat auf 127.0.0.1:5059 gestartet. Port 5057 läuft weiter.')
        return state

    def activate(self, state):
        if state['port'] == 5057:
            print('Neue Version ist bereits auf 5057 aktiv.');return
        if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            raise InstallError('Sichere Prozessablösung benötigt Linux-pidfd; keine Abschaltung')
        try:
            public_probe(state['origin'])
        except (OSError, ValueError):
            raise InstallError('Öffentlicher KI-Endpunkt vor Aktivierung nicht prüfbar; Altversion bleibt aktiv') from None
        launch = discover_old(self.old)
        if launch['pid'] != state['old_pid'] or launch['start'] != state['old_start']:
            raise InstallError('Altprozess hat sich geändert; keine automatische Abschaltung')
        fd = os.pidfd_open(launch['pid'])
        try:
            again = discover_old(self.old)
            if (again['pid'], again['start']) != (launch['pid'], launch['start']):
                raise InstallError('Altprozesswechsel erkannt; Aktivierung abgebrochen')
            # Keep a fresh, private rollback environment. No credential is used for tests.
            private_write(self.root / 'private/rollback-launch.json', json.dumps(launch))
            self.run(['sudo', '-v'], 'Dienstfreigabe')
            self.run(['sudo', '-n', 'systemctl', 'stop', UNIT], 'Kandidat anhalten')
            self.write_unit(Path(state['release']), 5057)
            try:
                signal.pidfd_send_signal(fd, signal.SIGTERM)
                for _ in range(50):
                    if not port_open(5057):break
                    time.sleep(0.2)
                if port_open(5057):
                    raise InstallError('Altprozess beendet sich nicht; kein SIGKILL und kein Port-Konflikt erzwungen')
                self.run(['sudo', '-n', 'systemctl', 'start', UNIT], 'Aktivierung')
                self.wait_health(5057, state['origin'])
                self.verify_listener(5057)
                public_probe(state['origin'], require_companion=True)
            except BaseException:
                subprocess.run(['sudo', '-n', 'systemctl', 'stop', UNIT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if not port_open(5057):
                    private_write(self.root / 'private/rollback.log', b'')
                    with (self.root / 'private/rollback.log').open('ab') as log:
                        subprocess.Popen(launch['argv'], cwd=self.old, env=launch['env'], stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=log, start_new_session=True)
                    self.wait_health(5057, state['origin'])
                else:
                    current = discover_old(self.old)
                    if (current['pid'], current['start']) != (launch['pid'], launch['start']):
                        raise InstallError('Rückkehr blockiert: fremder Prozess auf 5057; keine weitere Abschaltung') from None
                # Old endpoint is restored (or was never stopped). Candidate remains off.
                self.write_unit(Path(state['release']), 5059)
                self.run(['sudo', '-n', 'systemctl', 'start', UNIT], 'Kandidat nach Rückkehr starten')
                raise InstallError('Aktivierung fehlgeschlagen; Rückkehr zur alten Installation ausgeführt oder Altprozess läuft weiter') from None
            state['port'] = 5057
            private_write(self.root / 'private/state.json', json.dumps(state, indent=2))
            print('Neue KI-Demo auf 5057 aktiv; öffentliche Proxy-Adresse unverändert. Portal 5000 nicht verändert.')
            print('Dienst läuft, Autostart ist absichtlich noch nicht aktiviert (alte Boot-Startmechanismen nicht verifiziert).')
        finally:
            os.close(fd)

    def rollback(self, state):
        if state['port'] != 5057:
            raise InstallError('Alte Installation läuft bereits; kein Rollback nötig')
        launch = json.loads((self.root / 'private/rollback-launch.json').read_text())
        if len(launch['argv']) != 2 or Path(launch['argv'][1]).name != 'run.py':
            raise InstallError('Ungültige Rückkehrinformationen')
        executable = Path(launch['argv'][0]);script = Path(launch['argv'][1])
        if not executable.is_absolute():executable = self.old / executable
        if not script.is_absolute():script = self.old / script
        if executable.resolve() != (self.old / '.venv/bin/python').resolve() or script.resolve() != (self.old / 'run.py').resolve():
            raise InstallError('Rückkehrpfad stimmt nicht mit alter Testinstallation überein')
        self.run(['sudo', '-v'], 'Dienstfreigabe')
        self.run(['sudo', '-n', 'systemctl', 'stop', UNIT], 'Neuen KI-Dienst stoppen')
        if port_open(5057):
            raise InstallError('Port 5057 weiterhin belegt; kein fremder Prozess wird beendet')
        private_write(self.root / 'private/rollback.log', b'')
        with (self.root / 'private/rollback.log').open('ab') as log:
            subprocess.Popen(launch['argv'], cwd=self.old, env=launch['env'], stdin=subprocess.DEVNULL,
                             stdout=log, stderr=log, start_new_session=True)
        self.wait_health(5057, state['origin'])
        self.write_unit(Path(state['release']), 5059)
        self.run(['sudo', '-n', 'systemctl', 'start', UNIT], 'Kandidat getrennt starten')
        self.wait_health(5059, state['origin'])
        state['port'] = 5059
        private_write(self.root / 'private/state.json', json.dumps(state, indent=2))
        print('Alte Version auf 5057 wiederhergestellt; neue Version getrennt auf 5059.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--rollback', action='store_true', help='nur neuen KI-Dienst zurücknehmen und alten Start wiederherstellen')
    actions.add_argument('--activate', action='store_true', help='nach erfolgreichen Tests nur KI-Port 5057 übernehmen')
    parser.add_argument('--source-zip', type=Path, help='optionales Archiv exakt des gepinnten Commits')
    parser.add_argument('--config', type=Path, help='bestehende private Konfiguration, falls nicht config.ini')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        account = pwd.getpwuid(os.getuid())
        if account.pw_name != 'pi' or os.getuid() == 0 or platform.system() != 'Linux':
            raise InstallError('Als Benutzer pi auf dem Pi ausführen, nicht mit sudo vor python3')
        if 'VERSION_CODENAME=bookworm' not in Path('/etc/os-release').read_text():
            raise InstallError('Dieses Skript ist für Debian/Raspberry Pi OS Bookworm geprüft')
        installer = Installer(Path(account.pw_dir))
        if args.rollback:
            installer.rollback(installer.load_state())
        else:
            state = installer.install(args.source_zip, args.config)
            if args.activate:installer.activate(state)
    except InstallError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except (OSError, ValueError, configparser.Error, subprocess.SubprocessError):
        print('Installation sicher angehalten. Bestehendes Portal wurde nicht verändert. Details/Anleitung prüfen.', file=sys.stderr)
        # Deliberately no exception body: it could contain configuration or subprocess data.
        raise SystemExit(1)


if __name__ == '__main__':
    main()

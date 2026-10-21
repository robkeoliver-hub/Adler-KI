#!/usr/bin/env python3
"""Prepare the reviewed private portal export in a NEW private test directory only."""
import argparse
import hashlib
import io
import json
import os
import platform
import pwd
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

SOURCE_COMMIT = 'f583caa88b14a1e7238b2d06b0bf0d8d747c0d0a'
SOURCE_MANIFEST = '6d28710d5c85c9411a1eefb9a293c842aa802e5e33dcfee11ff7a1ad6a813128'
EXPORT_HASH = '536a6a72407b8f6a370e8f294f88d78b0c51de9cdc6e007dcbcedc237f298770'
LIMIT = 20 * 1024 * 1024
PORT = 5071
DEPENDENCIES = ['Flask==3.1.3', 'waitress==3.0.2', 'Flask-SQLAlchemy==3.1.1',
                'SQLAlchemy==2.0.44', 'Pillow==12.0.0', 'pytesseract==0.3.13', 'qrcode==8.2']


class StageError(Exception):
    pass


def private_write(path, data):
    if path.is_symlink():
        raise StageError('Unsicherer Dateipfad')
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.private-')
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data.encode() if isinstance(data, str) else data)
            out.flush(); os.fsync(out.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def zip_files(raw):
    if len(raw) > LIMIT:
        raise StageError('Archiv zu groß')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries = z.infolist()
            if len(entries) > 1000 or sum(i.file_size for i in entries) > LIMIT:
                raise StageError('Archivlimits überschritten')
            result, seen, roots = {}, set(), set()
            for info in entries:
                name = info.filename; parts = PurePosixPath(name).parts
                if (not parts or name.startswith('/') or '\\' in name or ':' in name
                        or '..' in parts or any(ord(c) < 32 for c in name)
                        or stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1):
                    raise StageError('Unsicherer Archiveintrag')
                key = name.casefold().rstrip('/')
                if key in seen:raise StageError('Doppelter Archiveintrag')
                seen.add(key); roots.add(parts[0])
                if info.is_dir():continue
                relative = '/'.join(parts[1:])
                if not relative or info.file_size > 2 * 1024 * 1024:
                    raise StageError('Unsicherer Archiveintrag')
                with z.open(info) as file:result[relative] = file.read(2 * 1024 * 1024 + 1)
            if len(roots) != 1:raise StageError('Mehrdeutige Archivwurzel')
            return result
    except (zipfile.BadZipFile, RuntimeError, ValueError, NotImplementedError):
        raise StageError('Archiv nicht lesbar') from None


def source_payload(raw):
    files = zip_files(raw); manifest = files.get('SHA256SUMS', b'')
    if hashlib.sha256(manifest).hexdigest() != SOURCE_MANIFEST:
        raise StageError('KI-Quellstand stimmt nicht mit geprüftem PR #7 überein')
    expected = {}
    try:
        for line in manifest.decode().splitlines():
            digest, name = line.split('  ', 1)
            if name in expected or len(digest) != 64:raise ValueError()
            expected[name] = digest
    except (UnicodeError, ValueError):
        raise StageError('Ungültiges Quellmanifest') from None
    if set(files) != set(expected) | {'SHA256SUMS'}:
        raise StageError('Ungeprüfte Quelldateien')
    if any(hashlib.sha256(files[p]).hexdigest() != h for p,h in expected.items()):
        raise StageError('Quelldatei-Prüfsumme falsch')
    return files


def export_payload(raw):
    if hashlib.sha256(raw).hexdigest() != EXPORT_HASH:
        raise StageError('Portalexport wurde geändert oder nicht geprüft; keine Ausführung')
    files = zip_files(raw)
    if not {'app.py','meyton_ocr.py','templates/base.html'} <= set(files):
        raise StageError('Portalexport unvollständig')
    for name,data in files.items():
        if (name.endswith(('.db','.sqlite','.sqlite3','.log','.pem','.key'))
                or any(p in {'.git','.venv','uploads','backups'} for p in PurePosixPath(name).parts)
                or data.startswith(b'SQLite format 3\x00')):
            raise StageError('Private Laufzeitdaten im Export')
    compile(files['app.py'], 'reviewed-export/app.py', 'exec')
    return files


def port_open():
    with socket.socket() as sock:
        sock.settimeout(.3)
        return sock.connect_ex(('127.0.0.1', PORT)) == 0


def owns_listener(pid):
    address = '0100007F:' + format(PORT, '04X')
    inodes = {line.split()[9] for line in Path('/proc/net/tcp').read_text().splitlines()[1:]
              if line.split()[1] == address and line.split()[3] == '0A'}
    for fd in (Path('/proc')/str(pid)/'fd').iterdir():
        try:
            target = str(fd.readlink())
            if any(target == 'socket:[' + inode + ']' for inode in inodes):return True
        except FileNotFoundError:pass
    return False


# This runner only ever imports the reviewed COPY after all paths/config are fixed.
RUNNER = r'''
import importlib.util
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if ROOT.name != 'ki-adler-portaltest' or ROOT.is_symlink():
    raise RuntimeError('Ungültige Testwurzel')
config = json.loads((ROOT/'private/config.json').read_text())
portal = ROOT/'portal'
if portal.is_symlink() or (portal/'schuetzenjugend.db').is_symlink():
    raise RuntimeError('Unsicherer Testdatenbankpfad')
# Do not inherit real club credentials, Flask env or external provider keys.
os.environ.clear()
os.environ.update(PATH=str(ROOT/'.venv/bin')+os.pathsep+'/usr/bin:/bin', LANG='C.UTF-8',
                  SECRET_KEY=config['secret'], BETREUER_PASSWORT=config['staff_password'],
                  COOKIE_SECURE='1')
sys.path.insert(0,str(portal))
spec = importlib.util.spec_from_file_location('isolated_portal',portal/'app.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
app,db = module.app,module.db
with app.app_context():
    if Path(db.engine.url.database).resolve() != (portal/'schuetzenjugend.db').resolve():
        raise RuntimeError('Testdatenbank außerhalb der Kopie')
app.config.update(ADLER_PORTAL_ENABLED=True, ADLER_PORTAL_TOKEN_REVIEWED=True,
                  ADLER_PORTAL_ORIGIN=config['origin'])
from portal_adler import init_portal_adler
init_portal_adler(app,youth_model=module.Jugendlicher,training_model=module.Training,event_model=module.Termin)
with app.app_context():
    if not (ROOT/'private/seeded').exists():
        if module.Jugendlicher.query.count() or module.Erwachsener.query.count() or module.Training.query.count() or module.Termin.query.count():
            raise RuntimeError('Testdatenbank enthält unerwartete Daten')
        for i,token in enumerate(config['tokens'],1):
            kid=module.Jugendlicher(vorname='Testkind '+str(i),nachname='NUR TEST',
                geburtsdatum='2013-01-01',geschlecht='männlich',aktiv=True,
                disziplin='Lichtpunkt Auflage',qr_token=token)
            db.session.add(kid);db.session.flush()
            db.session.add(module.Training(jugendlicher_id=kid.id,datum=date.today().isoformat(),
                disziplin='Lichtpunkt Auflage',ringzahl=100+i*11,schuss_anzahl=20))
        db.session.add(module.Termin(titel='TESTTERMIN – kein echter Vereinstermin',
            datum=(date.today()+timedelta(days=1)).isoformat(),uhrzeit='17:00',zielgruppe='Jugend',ort='Nur Test'))
        db.session.commit()
        (ROOT/'private/seeded').write_text('synthetic-only\n')
    if module.Jugendlicher.query.count()!=2 or module.Erwachsener.query.count()!=0:
        raise RuntimeError('Unerwartete Personen im Testbestand')

@app.before_request
def read_only_test():
    from flask import abort,request
    if request.method not in ('GET','HEAD','OPTIONS') and request.endpoint not in (
        'portal_adler.bind','portal_adler.tool','portal_adler.close'):
        abort(403)


def selftest():
    import re
    count=0
    for i,token in enumerate(config['tokens']):
        c=app.test_client()
        for suffix in ('','/ergebnisse','/abzeichen','/termine','/kontakt-downloads'):
            response=c.get('/jugend/'+token+suffix,base_url=config['origin'])
            assert response.status_code==200
            assert b'ISOLIERTER PORTALTEST' in response.data
            assert b'portal-adler-dialog' in response.data
            count+=1
        response=c.get('/jugend/'+token,base_url=config['origin'])
        csrf=re.search(r'data-csrf="([^"]+)"',response.text).group(1)
        headers={'Origin':config['origin'],'X-CSRF-Token':csrf}
        def post(path,value):return c.post('/ki-adler/'+path,json=value,headers=headers,base_url=config['origin'])
        bound=post('session',{'token':token});assert bound.status_code==200
        headers['X-Adler-Binding']=bound.json['binding']
        result=post('tool',{'tool':'last_training'})
        assert result.status_code==200 and result.json['data']['score']==111+i*11
        assert post('tool',{'tool':'last_training','member_id':999}).status_code==400
        assert post('tool',{'tool':'next_event'}).json['data']['title'].startswith('TESTTERMIN')
        assert post('close',{}).status_code==200
        assert post('tool',{'tool':'last_training'}).status_code==401
        count+=6
    assert app.test_client().post('/betreuer/login',data={'passwort':'anything'}).status_code==403
    print(json.dumps({'ok':True,'checks':count+1,'synthetic_only':True,'port':5071}))

if __name__=='__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
    elif sys.argv[1:] == ['serve']:
        from waitress import serve
        serve(app,host='127.0.0.1',port=5071,threads=4)
    else:
        raise RuntimeError('Ungültige Aktion')
'''


class Stage:
    def __init__(self, home):
        self.home = Path(home).resolve()
        self.root = self.home/'ki-adler-portaltest'
        self.config = self.root/'private/config.json'

    def run(self, args, timeout=900):
        with (self.root/'private/setup.log').open('ab') as log:
            result = subprocess.run(args, cwd=self.root, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=log, timeout=timeout)
        if result.returncode:raise StageError('Testaufbau angehalten; privates setup.log lokal prüfen')

    def prepare(self, export, source_raw=None):
        # Validate before creating anything. Never overwrite an existing directory.
        files = export_payload(Path(export).read_bytes())
        if self.root.exists() or self.root.is_symlink():
            raise StageError('Testordner existiert bereits; keine Neuinstallation. --start/--status/--stop verwenden')
        if port_open():raise StageError('Port 5071 belegt; kein Prozess wird beendet')
        if source_raw is None:
            url='https://codeload.github.com/robkeoliver-hub/Adler-KI/zip/'+SOURCE_COMMIT
            with urllib.request.urlopen(url, timeout=40) as response:source_raw=response.read(LIMIT+1)
        source=source_payload(source_raw)
        self.root.mkdir(mode=0o700)
        (self.root/'private').mkdir(mode=0o700)
        private_write(self.root/'private/setup.log',b'')
        private_write(self.root/'private/state.json',json.dumps({'source':SOURCE_COMMIT,'export':EXPORT_HASH,'ready':False}))
        portal=self.root/'portal';portal.mkdir(mode=0o700)
        for name,data in files.items():
            path=portal/name;path.parent.mkdir(parents=True,exist_ok=True);private_write(path,data)
        for name,data in source.items():
            if name.startswith('portal_adler/'):
                path=portal/name;path.parent.mkdir(parents=True,exist_ok=True);private_write(path,data)
        base=portal/'templates/base.html';text=base.read_text()
        if text.count('</body>')!=1 or 'ki_adler_panel' in text:
            raise StageError('Basistemplate weicht vom geprüften Integrationspunkt ab')
        # In the isolated copy only, prevent root-scope PWA registration.
        registration="navigator.serviceWorker.register('/service-worker.js')"
        if text.count(registration)!=1:raise StageError('PWA-Testschutz nicht eindeutig anwendbar')
        text=text.replace(registration,"Promise.reject(new Error('PWA im isolierten Test deaktiviert'))")
        text=text.replace('<body>', '<body><aside role="note" style="background:#ffe080;color:#111;padding:12px;text-align:center">ISOLIERTER PORTALTEST – künstliche Daten; Änderungen gesperrt</aside>')
        if 'ISOLIERTER PORTALTEST' not in text:raise StageError('Testbanner fehlt')
        private_write(base,text.replace('</body>','{{ ki_adler_panel() }}</body>'))
        # Never copy credentials, DBs, uploads or environments from the live portal.
        config={'secret':secrets.token_urlsafe(48),'staff_password':secrets.token_urlsafe(48),
                'tokens':[secrets.token_urlsafe(32),secrets.token_urlsafe(32)],
                'origin':'https://adlerzug.duckdns.org'}
        private_write(self.config,json.dumps(config))
        private_write(self.root/'runner.py',RUNNER)
        self.run([sys.executable,'-m','venv',str(self.root/'.venv')])
        python=str(self.root/'.venv/bin/python')
        self.run([python,'-m','pip','install','--disable-pip-version-check',*DEPENDENCIES])
        self.run([python,str(self.root/'runner.py'),'selftest'],timeout=120)
        # Save hashes of every shipped/copied code file; refuse changed start code.
        manifest={str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(portal.rglob('*')) if p.is_file() and p.suffix in ('.py','.html','.js','.css')}
        manifest['runner.py']=hashlib.sha256((self.root/'runner.py').read_bytes()).hexdigest()
        private_write(self.root/'private/code-hashes.json',json.dumps(manifest))
        private_write(self.root/'private/state.json',json.dumps({'source':SOURCE_COMMIT,'export':EXPORT_HASH,'ready':True}))
        private_write(self.root/'private/access.json',json.dumps({'paths':['/jugend/'+t for t in config['tokens']],
            'warning':'Nur fuer lokalen Test bzw. spaeter freigegebenen HTTPS-Testproxy; niemals Produktivdaten eingeben.'}))
        print('Portal-Kopie und zwei künstliche Testkonten vorbereitet; integrierte Portaltests bestanden.')

    def validate(self):
        if self.root.is_symlink() or self.root.resolve()!=self.home/'ki-adler-portaltest':
            raise StageError('Ungültige Testwurzel')
        state=json.loads((self.root/'private/state.json').read_text())
        if state!={'source':SOURCE_COMMIT,'export':EXPORT_HASH,'ready':True}:
            raise StageError('Testaufbau nicht vollständig oder Quellstand verändert')
        hashes=json.loads((self.root/'private/code-hashes.json').read_text())
        for name,digest in hashes.items():
            path=self.root/name
            if not path.resolve().is_relative_to(self.root) or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise StageError('Testcode wurde nach der Prüfung verändert; kein Start')
        if (self.root/'portal/schuetzenjugend.db').is_symlink():raise StageError('Unsicherer Datenbankpfad')

    def process(self):
        path=self.root/'private/process.json'
        if not path.exists():return None
        state=json.loads(path.read_text());pid=state['pid'];proc=Path('/proc')/str(pid)
        try:
            fields=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()
            if fields[0]=='Z':return None
            current=fields[19]
            args=[a.decode() for a in proc.joinpath('cmdline').read_bytes().split(b'\0') if a]
            if (current!=state['start'] or proc.stat().st_uid!=os.getuid()
                    or proc.joinpath('cwd').resolve()!=self.root
                    or args!=[str(self.root/'.venv/bin/python'),str(self.root/'runner.py'),'serve']):
                raise StageError('PID gehört nicht zum geprüften Testprozess; keine Abschaltung')
        except FileNotFoundError:return None
        return state

    def start(self):
        self.validate()
        if self.process():print('Getrennter Portaltest läuft bereits; keine zweite Instanz.');return
        if port_open():raise StageError('Port 5071 belegt; kein fremder Prozess wird beendet')
        private_write(self.root/'private/server.log',b'')
        with (self.root/'private/server.log').open('ab') as log:
            proc=subprocess.Popen([str(self.root/'.venv/bin/python'),str(self.root/'runner.py'),'serve'],
                cwd=self.root,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        try:
            for _ in range(50):
                if proc.poll() is not None:raise StageError('Portaltest startet nicht; privates server.log lokal prüfen')
                if port_open():break
                time.sleep(.1)
            if not port_open():raise StageError('Portaltest startet zu langsam; sicher angehalten')
            if not owns_listener(proc.pid):raise StageError('Listener gehört nicht zum neuen Testprozess')
            # Direct local synthetic public page only; no proxy or credentials.
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:5071/',timeout=5) as r:
                if r.status!=200 or b'ISOLIERTER PORTALTEST' not in r.read(1024*1024):
                    raise StageError('Testbanner nicht erreichbar')
            start=(Path('/proc')/str(proc.pid)/'stat').read_text().rsplit(')',1)[1].split()[19]
            private_write(self.root/'private/process.json',json.dumps({'pid':proc.pid,'start':start}))
        except BaseException:
            if proc.poll() is None:proc.terminate()
            raise
        print('Portaltest läuft getrennt auf 127.0.0.1:5071. Ports 5000/5057, Nginx und systemd unverändert.')
        print('Noch kein iPhone-Link: sichere HTTPS-Testweiterleitung muss separat geprüft und freigegeben werden.')

    def stop(self):
        state=self.process()
        if not state:print('Kein zugehöriger Portaltest-Prozess aktiv.');return
        if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
            raise StageError('Sicheres Stoppen benötigt Linux-pidfd; keine PID-Abschaltung')
        fd=os.pidfd_open(state['pid'])
        try:
            if self.process()!=state:raise StageError('Prozesswechsel erkannt; kein Stop')
            signal.pidfd_send_signal(fd,signal.SIGTERM)
        finally:os.close(fd)
        for _ in range(50):
            if not self.process():
                (self.root/'private/process.json').unlink(missing_ok=True)
                print('Nur der eigene Portaltest gestoppt; alle Testdateien bleiben erhalten.');return
            time.sleep(.1)
        raise StageError('Testprozess beendet sich nicht; kein SIGKILL')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    actions=p.add_mutually_exclusive_group()
    actions.add_argument('--start',action='store_true')
    actions.add_argument('--stop',action='store_true')
    actions.add_argument('--status',action='store_true')
    args=p.parse_args();os.umask(0o077)
    try:
        user=pwd.getpwuid(os.getuid())
        if user.pw_name!='pi' or os.getuid()==0 or platform.system()!='Linux':
            raise StageError('Als pi auf dem Raspberry Pi ausführen, nicht sudo python3')
        if 'VERSION_CODENAME=bookworm' not in Path('/etc/os-release').read_text():
            raise StageError('Nur für Bookworm vorgesehen')
        stage=Stage(user.pw_dir)
        if args.stop:stage.stop()
        elif args.status:print('Portaltest aktiv' if stage.process() else 'Portaltest nicht aktiv')
        elif args.start:stage.start()
        else:
            stage.prepare(Path(user.pw_dir)/'ki-adler-portal-export.zip')
            stage.start()
    except StageError as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
    except (OSError,ValueError,KeyError,SyntaxError,subprocess.SubprocessError):
        print('Testaufbau angehalten. Private Logs lokal prüfen; Portal und KI-Demo unverändert.',file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':main()

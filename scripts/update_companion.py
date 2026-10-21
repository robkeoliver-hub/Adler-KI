#!/usr/bin/env python3
"""One reversible update of the EXISTING synthetic portal test, never port 5000/5057."""
import argparse
import hashlib
import io
import json
import os
import platform
import pwd
import runpy
import sqlite3
import stat
import sys
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

# Filled by release preparation after verified source publication. Never tracks main.
SOURCE_COMMIT = 'dcfee509a3a86c1214ce329ca50a089f9fe3fea7'
PACKAGE_HASHES = {'portal_adler/__init__.py': '05397432f36d7f2ce9f9341a0fc3a63e0e4d31d02f7de387b29ef50d4e7be309', 'portal_adler/dialogue.py': 'b611783f5ce5def4b6f8174baa37175a888236411fc4e3e1a64d2e364f67d37e', 'portal_adler/static/panel.js': '9c82421fa04ef014ae8e41c9349e9820c9af175bdc10593aa38633c3c3af0c71', 'portal_adler/static/panel.css': 'f841a3bd84d72600b4d8731a57f73e746a263bcc2877df26e3794d26945be89c', 'portal_adler/templates/portal_adler/panel.html': 'cc79749dc0aa3862b078cb8dcb677cf62049c84a17c5b9b4aab303b314742f98', 'portal_adler/static/art/adler-atlas.webp.base64': 'faa4ec07b50e4143589dc16658a6401a02c0cab7075fb3d970b9b1b463ea41b6'}
CONTROLLER_HASH = 'd29254457d8aa25f0dad6e5021dcf6e6c850410a0a9e210d444cd3b0cc185ef2'
OLD_RUNNER_HASH = '1e935a89921f194f21d3d8d03edb5ce98ee6fd1728dd4473e86a8d58ff93cf22'
OLD_PACKAGE_HASHES = {'portal_adler/__init__.py': ['06b7c5872878d9019ae25274a8d37ca913e9a42916644294ebeeaba91cade048'], 'portal_adler/static/panel.js': ['4b1e04ac9ff363e03c94caeb65a34b32dc676dfaba1891e962b21e38c0036859'], 'portal_adler/static/panel.css': ['8882f9fa217dbbabc1a42a4df548f4f87564825d25b9b094aaab1e7a977d12ad', '3d5ec1dfe311ed199629addbd74e10c3c8d877b98d79b6e7e9da6db2d3a9789f'], 'portal_adler/templates/portal_adler/panel.html': ['f8692d56dc5b523a0e2759fe561ffc2453517488d74c717154cb352e9f1d85aa']}
PREFIX='/demo/ki-adler-portaltest'
LIMIT=20*1024*1024


class UpdateError(Exception):pass


def sha(data):return hashlib.sha256(data).hexdigest()


def unpack(raw):
    if len(raw)>LIMIT:raise UpdateError('Quellarchiv zu groß')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries=z.infolist()
            if len(entries)>1000 or sum(e.file_size for e in entries)>LIMIT:raise ValueError()
            files={};seen=set();roots=set()
            for entry in entries:
                p=PurePosixPath(entry.filename)
                if (p.is_absolute() or '..' in p.parts or '\\' in entry.filename or ':' in entry.filename
                        or stat.S_ISLNK(entry.external_attr>>16) or entry.flag_bits&1
                        or any(ord(c)<32 for c in entry.filename)):raise ValueError()
                roots.add(p.parts[0]);name='/'.join(p.parts[1:])
                if entry.filename.casefold().rstrip('/') in seen:raise ValueError()
                seen.add(entry.filename.casefold().rstrip('/'))
                if entry.is_dir():continue
                if not name or entry.file_size>2*1024*1024:raise ValueError()
                if name in PACKAGE_HASHES:files[name]=z.read(entry)
        if len(roots)!=1 or set(files)!=set(PACKAGE_HASHES):raise ValueError()
        if any(sha(data)!=PACKAGE_HASHES[name] for name,data in files.items()):raise ValueError()
        return files
    except (zipfile.BadZipFile,ValueError,RuntimeError):
        raise UpdateError('Ungeprüftes oder unsicheres Quellarchiv') from None


def patched_runner(raw):
    if sha(raw)!=OLD_RUNNER_HASH:raise UpdateError('Unbekannter Test-Runner; keine Änderung')
    text=raw.decode()
    old='init_portal_adler(app,youth_model=module.Jugendlicher,training_model=module.Training,event_model=module.Termin)'
    replacement="""from portal_adler.dialogue import load_private_settings
app.config.update(load_private_settings(ROOT/'private/dialogue.json'))
init_portal_adler(app,youth_model=module.Jugendlicher,training_model=module.Training,event_model=module.Termin,
                  adult_model=module.Erwachsener,adult_training_model=module.ErwachsenenTraining,
                  badge_reader=module.get_abzeichen_status)"""
    if text.count(old)!=1 or text.count("'portal_adler.bind','portal_adler.tool','portal_adler.close'")!=1:
        raise UpdateError('Unbekannte Teststruktur')
    text=text.replace(old,replacement).replace("'portal_adler.bind','portal_adler.tool','portal_adler.close'", "'portal_adler.bind','portal_adler.tool','portal_adler.chat','portal_adler.close'")
    check="""
        assert bound.json['profile']['display_name']=='Testkind '+str(i+1)
        greeting=post('chat',{'text':'Wie geht es dir?','external_consent':False})
        assert greeting.status_code==200 and greeting.json['source']=='local'
        badges=post('tool',{'tool':'badges'})
        assert badges.status_code==200 and badges.json['source']=='portal'
        assert c.get(PREFIX+'/ki-adler/avatar.webp',base_url=config['origin']).data[:4]==b'RIFF'
"""
    needle="        headers['X-Adler-Binding']=bound.json['binding']"
    if text.count(needle)!=1:raise UpdateError('Testprüfung fehlt')
    text=text.replace(needle,needle+check)
    compile(text,'test-runner','exec')
    return text.encode()


class Updater:
    def __init__(self,home,files):
        self.home=Path(home).resolve();self.root=self.home/'ki-adler-portaltest';self.files=files
        controller=self.home/'prepare_portal_test.py'
        if controller.is_symlink() or sha(controller.read_bytes())!=CONTROLLER_HASH:
            raise UpdateError('Unbekannte Installationssteuerung; keine Ausführung')
        self.api=runpy.run_path(str(controller));self.stage=self.api['Stage'](self.home)
        self.backup=self.root/'private/companion-backup-v1';self.marker=self.root/'private/companion-update.json'

    def safe(self,name):
        path=self.root/name
        if not path.resolve().is_relative_to(self.root):raise UpdateError('Unsicherer Testpfad')
        current=path
        while current!=self.home:
            if current.is_symlink():raise UpdateError('Unsicherer Testpfad')
            current=current.parent
        return path

    def write(self,name,data):
        path=self.safe(name);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.api['private_write'](path,data)

    def wait_port_free(self):
        # Process exit can precede socket release; wait briefly, never kill strangers.
        for _ in range(20):
            if not self.api['port_open']():return
            time.sleep(.05)
        raise UpdateError('Port 5071 bleibt belegt; kein fremder Prozess wird beendet')

    def backup_db(self,source,target):
        if source.is_symlink() or target.is_symlink():raise UpdateError('Unsicherer Datenbankpfad')
        with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as src:
            with sqlite3.connect(target) as dst:src.backup(dst)
        os.chmod(target,0o600)

    def save(self,updates):
        if self.backup.exists() or self.backup.is_symlink():raise UpdateError('Sicherung existiert bereits')
        self.backup.mkdir(mode=0o700);saved={}
        for index,name in enumerate(updates):
            path=self.safe(name);data=path.read_bytes() if path.exists() else None
            leaf='file-'+str(index)
            if data is not None:self.api['private_write'](self.backup/leaf,data)
            saved[name]={'file':leaf,'old':sha(data) if data is not None else None,'new':sha(updates[name]) if name in updates else None}
        self.backup_db(self.safe('portal/schuetzenjugend.db'),self.backup/'synthetic.db')
        self.api['private_write'](self.backup/'manifest.json',json.dumps({'files':saved,'db':sha((self.backup/'synthetic.db').read_bytes())}))

    def restore(self):
        manifest_path=self.safe('private/companion-backup-v1/manifest.json')
        manifest=json.loads(manifest_path.read_text())
        allowed={'portal/'+p for p in PACKAGE_HASHES}|{'runner.py','private/dialogue.json','private/code-hashes.json'}
        if set(manifest['files'])!=allowed:raise UpdateError('Ungültige Sicherungsdateiliste')
        database=self.safe('private/companion-backup-v1/synthetic.db')
        if sha(database.read_bytes())!=manifest['db']:raise UpdateError('Datenbanksicherung beschädigt')
        originals={}
        for name,item in manifest['files'].items():
            self.safe(name);leaf=item['file']
            if not leaf.startswith('file-') or not leaf[5:].isdigit():raise UpdateError('Unsicherer Sicherungspfad')
            if self.safe(name).exists() and sha(self.safe(name).read_bytes()) not in {item['old'],item['new']}:
                raise UpdateError('Später geänderte Datei; Rücknahme angehalten')
            if item['old'] is None:
                originals[name]=None
            else:
                data=self.safe('private/companion-backup-v1/'+leaf).read_bytes()
                if sha(data)!=item['old']:raise UpdateError('Sicherung beschädigt')
                originals[name]=data
        self.stage.stop()
        self.wait_port_free()
        for name,data in originals.items():
            if data is None:self.safe(name).unlink(missing_ok=True)
            else:self.write(name,data)
        self.backup_db(database,self.safe('portal/schuetzenjugend.db'))
        self.stage.validate();self.stage.start()
        self.write('private/companion-update.json',json.dumps({'status':'rolled_back','source':SOURCE_COMMIT}))
        print('Vorheriger Portaltest und Konfiguration wiederhergestellt. Nginx und Port 5000/5057 unverändert.')

    def apply(self):
        self.stage.validate()
        if self.marker.exists():
            marker=json.loads(self.marker.read_text())
            if marker=={'status':'applied','source':SOURCE_COMMIT}:
                self.stage.run([str(self.root/'.venv/bin/python'),str(self.root/'runner.py'),'selftest'],timeout=120)
                self.stage.start();print('KI-Adler-Begleiter ist bereits aktualisiert.');return
            raise UpdateError('Vorheriger Updateversuch vorhanden; keine Überschreibung')
        for name,digests in OLD_PACKAGE_HASHES.items():
            if sha(self.safe('portal/'+name).read_bytes()) not in digests:
                raise UpdateError('Unerwartete frühere Adler-Version; keine Überschreibung')
        updates={'portal/'+p:data for p,data in self.files.items()}
        updates['runner.py']=patched_runner(self.safe('runner.py').read_bytes())
        # Never overwrite a pre-existing provider credential file.
        if self.safe('private/dialogue.json').exists():raise UpdateError('Private KI-Konfiguration existiert bereits; manuelle Prüfung erforderlich')
        updates['private/dialogue.json']=json.dumps({'ADLER_DIALOGUE_PROVIDER':'off','ADLER_DIALOGUE_APPROVED':False,
            'ADLER_DIALOGUE_ENDPOINT':'','ADLER_DIALOGUE_MODEL':'','ADLER_DIALOGUE_KEY':'',
            'ADLER_DIALOGUE_PROCESSOR_NOTICE':''}).encode()
        hashes=json.loads(self.safe('private/code-hashes.json').read_text())
        hashes.update({name:sha(data) for name,data in updates.items() if name!='private/dialogue.json'})
        updates['private/code-hashes.json']=json.dumps(hashes).encode()
        self.stage.stop()
        self.wait_port_free()
        complete=False
        try:
            self.save(updates);complete=True
            self.write('private/companion-update.json',json.dumps({'status':'pending','source':SOURCE_COMMIT}))
            for name,data in updates.items():self.write(name,data)
            self.stage.run([str(self.root/'.venv/bin/python'),str(self.root/'runner.py'),'selftest'],timeout=120)
            self.stage.start()
            self.write('private/companion-update.json',json.dumps({'status':'applied','source':SOURCE_COMMIT}))
        except BaseException:
            if complete:self.restore()
            else:self.stage.start()
            raise UpdateError('Update fehlgeschlagen; vorheriger Teststand wieder gestartet') from None
        print('Freundlicher KI-Adler mit persönlichem QR-Zugang im bestehenden Portaltest bereit.')
        print('Bestehende Testlinks und HTTPS-Pfad bleiben gleich. Keine Nginx-/Produktivänderung.')
        print('Freier KI-Dienst bewusst noch aus; Portalantworten und Begrüßung funktionieren lokal.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rollback',action='store_true');args=parser.parse_args()
    os.umask(0o077)
    try:
        account=pwd.getpwuid(os.getuid())
        if account.pw_name!='pi' or os.getuid()==0 or platform.system()!='Linux':raise UpdateError('Als pi ausführen, ohne sudo')
        home=Path(account.pw_dir);cache=home/'ki-adler-portaltest/private/companion-source.zip'
        if cache.is_symlink():raise UpdateError('Unsicherer Quellcache')
        if cache.exists():
            with cache.open('rb') as stream:raw=stream.read(LIMIT+1)
        elif args.rollback:raise UpdateError('Geprüfter Offline-Quellcache fehlt')
        else:
            with urllib.request.urlopen('https://codeload.github.com/robkeoliver-hub/Adler-KI/zip/'+SOURCE_COMMIT,timeout=40) as r:raw=r.read(LIMIT+1)
        updater=Updater(home,unpack(raw))
        if not cache.exists():updater.write('private/companion-source.zip',raw)
        if args.rollback:updater.restore()
        else:updater.apply()
    except UpdateError as error:print(str(error),file=sys.stderr);raise SystemExit(1)
    except Exception:
        print('Update sicher angehalten. Private lokale Logs prüfen; keine Zugangsdaten weitergeben.',file=sys.stderr);raise SystemExit(1)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Update ONLY the existing synthetic portal test. Never writes nginx config."""
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
import urllib.request
import zipfile
from pathlib import Path,PurePosixPath

COMMIT='1b25ed14325cf72906a4bfadfcd71ec56936673f'
MANIFEST='3d97f7a666dd2ba12ee6a7c9c6f28edc0609cf5e1edd07a21f7ecb40dad65fec'
PREFIX='/demo/ki-adler-portaltest'
LIMIT=20*1024*1024
ASSETS=['portal_adler/static/panel.js','portal_adler/templates/portal_adler/panel.html','portal_adler/testing_mount.py']
OLD={'portal/portal_adler/static/panel.js':'8aad85da031cd5897eb4329c660729656a140ccc404e9c79aedd668d33078550',
     'portal/portal_adler/templates/portal_adler/panel.html':'af5c39717a0a41b58f00f71b89ea296d29eec307d30bf19ca875ae4d4ce4c573'}


class UpdateError(Exception):pass


def sha(data):return hashlib.sha256(data).hexdigest()


def payload(raw):
    if len(raw)>LIMIT:raise UpdateError('Quellarchiv zu groß')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries=z.infolist()
            if len(entries)>1000 or sum(i.file_size for i in entries)>LIMIT:raise UpdateError('Archivlimits überschritten')
            files={};roots=set()
            for i in entries:
                p=PurePosixPath(i.filename);parts=p.parts
                if (not parts or p.is_absolute() or '..' in parts or '\\' in i.filename or ':' in i.filename
                        or stat.S_ISLNK(i.external_attr>>16) or i.flag_bits&1):raise UpdateError('Unsicheres Archiv')
                roots.add(parts[0])
                if i.is_dir():continue
                name='/'.join(parts[1:])
                if not name or name in files or i.file_size>2*1024*1024:raise UpdateError('Ungültiges Archiv')
                files[name]=z.read(i)
        if len(roots)!=1 or sha(files.get('SHA256SUMS',b''))!=MANIFEST:raise UpdateError('Ungeprüfter Quellstand')
        expected={}
        for line in files['SHA256SUMS'].decode().splitlines():
            digest,name=line.split('  ',1)
            if name in expected:raise UpdateError('Doppeltes Manifest')
            expected[name]=digest
        if set(files)!=set(expected)|{'SHA256SUMS'} or any(sha(files[n])!=h for n,h in expected.items()):
            raise UpdateError('Quellprüfsumme falsch')
        return files
    except (zipfile.BadZipFile,ValueError,UnicodeError,RuntimeError):
        raise UpdateError('Quellarchiv nicht lesbar') from None


SELFTEST=r'''
def selftest():
    import re
    from werkzeug.test import Client
    from werkzeug.wrappers import Response
    count=0
    for i,token in enumerate(config['tokens']):
        c=Client(application,Response)
        c.set_cookie('session','synthetic-production-cookie',domain='adlerzug.duckdns.org')
        for suffix in ('','/ergebnisse','/abzeichen','/termine','/kontakt-downloads'):
            response=c.get(PREFIX+'/jugend/'+token+suffix,base_url=config['origin'])
            assert response.status_code==200 and 'ISOLIERTER PORTALTEST' in response.text
            assert 'data-prefix="'+PREFIX+'"' in response.text
            assert PREFIX+'/ki-adler/static/panel.js' in response.text
            count+=1
        csrf=re.search(r'data-csrf="([^"]+)"',response.text).group(1)
        headers={'Origin':config['origin'],'X-CSRF-Token':csrf}
        def post(path,value):return c.post(PREFIX+'/ki-adler/'+path,json=value,headers=headers,base_url=config['origin'])
        bound=post('session',{'token':token});assert bound.status_code==200
        headers['X-Adler-Binding']=bound.json['binding']
        result=post('tool',{'tool':'last_training'})
        assert result.status_code==200 and result.json['data']['score']==111+i*11
        assert post('tool',{'tool':'last_training','member_id':999}).status_code==400
        event=post('tool',{'tool':'next_event'});assert event.status_code==200
        if event.json['data'] is not None:assert event.json['data']['title'].startswith('TESTTERMIN')
        assert post('close',{}).status_code==200 and post('tool',{'tool':'last_training'}).status_code==401
        assert c.get_cookie('session',domain='adlerzug.duckdns.org').value=='synthetic-production-cookie'
        count+=7
    c=Client(application,Response)
    assert c.get('/jugend/'+config['tokens'][0],base_url=config['origin']).status_code==404
    assert c.get('/',base_url=config['origin']).status_code==200
    assert c.post(PREFIX+'/betreuer/login',data={'passwort':'anything'},base_url=config['origin']).status_code==403
    print(json.dumps({'ok':True,'checks':count+3,'synthetic_only':True,'mounted':PREFIX}))

'''


def runner(old):
    start=old.find('def selftest():');end=old.find("if __name__=='__main__':")
    if start<0 or end<start or old.count("serve(app,host='127.0.0.1',port=5071,threads=4)")!=1:
        raise UpdateError('Unbekannte Runnerstruktur')
    mount="\nfrom portal_adler.testing_mount import PREFIX, mount_isolated_test\napp.config['ADLER_ISOLATED_TEST']=True\napplication=mount_isolated_test(app)\n\n"
    new=old[:start]+mount+SELFTEST+old[end:]
    new=new.replace("serve(app,host='127.0.0.1',port=5071,threads=4)","serve(application,host='127.0.0.1',port=5071,threads=4)")
    compile(new,'isolated-runner','exec');return new.encode()


class Updater:
    def __init__(self,home,files):
        self.home=Path(home).resolve();self.root=self.home/'ki-adler-portaltest';self.files=files
        controller=self.home/'prepare_portal_test.py'
        if controller.is_symlink() or controller.read_bytes()!=files['scripts/prepare_portal_test.py']:
            raise UpdateError('Installationssteuerung wurde verändert; keine Ausführung')
        self.api=runpy.run_path(str(controller));self.stage=self.api['Stage'](self.home)
        self.backup=self.root/'private/https-backup-v1'
        self.marker=self.root/'private/https-update.json'

    def safe(self,name):
        p=self.root/name
        if p.is_symlink() or not p.resolve().is_relative_to(self.root):raise UpdateError('Unsicherer Testpfad')
        return p

    def write(self,name,data):self.api['private_write'](self.safe(name),data)

    def db_backup(self,source,target):
        if source.is_symlink() or target.is_symlink():raise UpdateError('Unsicherer Testdatenbankpfad')
        with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as src:
            with sqlite3.connect(target) as dst:src.backup(dst)
        os.chmod(target,0o600)

    def save_backup(self,names):
        if self.backup.exists() or self.backup.is_symlink():raise UpdateError('Updatesicherung existiert bereits; keine Überschreibung')
        self.backup.mkdir(mode=0o700)
        saved={}
        for index,name in enumerate(names):
            p=self.safe(name)
            if not p.exists():saved[name]=None;continue
            data=p.read_bytes();leaf='file-'+str(index)
            self.api['private_write'](self.backup/leaf,data)
            saved[name]={'file':leaf,'sha':sha(data)}
        database=self.safe('portal/schuetzenjugend.db')
        self.db_backup(database,self.backup/'synthetic.db')
        self.api['private_write'](self.backup/'manifest.json',json.dumps({'files':saved,'db_sha':sha((self.backup/'synthetic.db').read_bytes())}))

    def restore(self):
        # No Stage.validate required: restoration must also work after a failed update.
        if self.backup.is_symlink() or (self.backup/'manifest.json').is_symlink() or (self.backup/'synthetic.db').is_symlink():raise UpdateError('Unsicherer Sicherungspfad')
        backup=json.loads((self.backup/'manifest.json').read_text())
        expected={'runner.py','private/code-hashes.json','private/access.json'}|{'portal/'+x for x in ASSETS}
        if set(backup['files'])!=expected:raise UpdateError('Ungültige Updatesicherung')
        if sha((self.backup/'synthetic.db').read_bytes())!=backup['db_sha']:raise UpdateError('Testsicherung beschädigt')
        originals={}
        for name,item in backup['files'].items():
            self.safe(name)
            if item is None:originals[name]=None;continue
            leaf=item['file']
            if not leaf.startswith('file-') or not leaf[5:].isdigit():raise UpdateError('Unsicherer Sicherungspfad')
            if (self.backup/leaf).is_symlink():raise UpdateError('Unsicherer Sicherungspfad')
            data=(self.backup/leaf).read_bytes()
            if sha(data)!=item['sha']:raise UpdateError('Testsicherung beschädigt')
            originals[name]=data
        self.stage.stop()
        if self.api['port_open']():raise UpdateError('Port 5071 fremd belegt; keine Rücknahme erzwungen')
        for name,data in originals.items():
            if data is None:
                p=self.safe(name)
                if p.exists():
                    if name!='portal/portal_adler/testing_mount.py' or p.read_bytes()!=self.files['portal_adler/testing_mount.py']:
                        raise UpdateError('Neue Testdatei unerwartet verändert; keine Löschung')
                    p.unlink()
            else:self.write(name,data)
        database=self.safe('portal/schuetzenjugend.db')
        self.db_backup(self.backup/'synthetic.db',database)
        self.stage.validate();self.stage.start()
        self.write('private/https-update.json',json.dumps({'status':'rolled_back','source':COMMIT}))
        print('Vorherige Testkopie auf 5071 wiederhergestellt; Nginx und Produktivdienste unverändert.')

    def apply(self):
        self.stage.validate()
        if self.marker.exists():
            status=json.loads(self.marker.read_text()).get('status')
            if status=='applied':
                self.stage.run([str(self.root/'.venv/bin/python'),str(self.root/'runner.py'),'selftest'],timeout=120)
                self.stage.start();print('HTTPS-Testmount ist bereits vorbereitet.');return
            raise UpdateError('Früherer Updateversuch vorhanden; nicht erneut überschreiben')
        for name,digest in OLD.items():
            if sha(self.safe(name).read_bytes())!=digest:raise UpdateError('Testassets entsprechen nicht dem geprüften Ausgangsstand')
        if self.safe('runner.py').read_text()!=self.api['RUNNER'] or self.safe('portal/portal_adler/testing_mount.py').exists():
            raise UpdateError('Testkopie wurde bereits anders verändert')
        updates={'runner.py':runner(self.api['RUNNER'])}
        updates.update({'portal/'+p:self.files[p] for p in ASSETS})
        names=list(updates)+['private/code-hashes.json','private/access.json']
        self.stage.stop()
        if self.api['port_open']():raise UpdateError('Port 5071 fremd belegt; kein Update')
        complete=False
        try:
            self.save_backup(names);complete=True
            self.write('private/https-update.json',json.dumps({'status':'pending','source':COMMIT}))
            for name,data in updates.items():self.write(name,data)
            hashes=json.loads(self.safe('private/code-hashes.json').read_text())
            hashes.update({name:sha(data) for name,data in updates.items()})
            self.write('private/code-hashes.json',json.dumps(hashes))
            access=json.loads(self.safe('private/access.json').read_text())
            if any(not p.startswith('/jugend/') for p in access['paths']):raise UpdateError('Unbekannte Testzugriffspfade')
            access['paths']=[PREFIX+p for p in access['paths']]
            self.write('private/access.json',json.dumps(access))
            self.stage.run([str(self.root/'.venv/bin/python'),str(self.root/'runner.py'),'selftest'],timeout=120)
            self.stage.start()
            self.write('private/https-update.json',json.dumps({'status':'applied','source':COMMIT}))
        except BaseException:
            if complete:self.restore()
            else:self.stage.start()
            raise UpdateError('Testupdate fehlgeschlagen; vorherige Testkopie wieder gestartet') from None
        print('Testkopie erfolgreich für HTTPS-Pfad und eigenes Cookie vorbereitet. Integrierte Tests bestanden.')
        print('Nginx unverändert: Der öffentliche Testlink ist noch NICHT aktiviert.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rollback',action='store_true');args=p.parse_args()
    os.umask(0o077)
    try:
        account=pwd.getpwuid(os.getuid())
        if account.pw_name!='pi' or os.getuid()==0 or platform.system()!='Linux':raise UpdateError('Als pi ausführen, nicht sudo python3')
        cache=Path(account.pw_dir)/'ki-adler-portaltest/private/mount-source.zip'
        if cache.exists():
            if cache.is_symlink():raise UpdateError('Unsicherer Quellcache')
            with cache.open('rb') as file:raw=file.read(LIMIT+1)
        elif args.rollback:raise UpdateError('Geprüfter Quellcache für Offline-Rücknahme fehlt')
        else:
            with urllib.request.urlopen('https://codeload.github.com/robkeoliver-hub/Adler-KI/zip/'+COMMIT,timeout=40) as r:raw=r.read(LIMIT+1)
        files=payload(raw)
        updater=Updater(account.pw_dir,files)
        if not cache.exists():updater.write('private/mount-source.zip',raw)
        if args.rollback:updater.restore()
        else:updater.apply()
    except UpdateError as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
    except Exception:
        print('Testupdate sicher angehalten. Private Logs lokal prüfen; keine Nginx-Änderung.',file=sys.stderr);raise SystemExit(1)


if __name__=='__main__':main()

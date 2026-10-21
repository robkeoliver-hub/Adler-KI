#!/usr/bin/env python3
"""Default: validate an isolated nginx candidate. --apply needs explicit approval."""
import argparse
import fcntl
import fnmatch
import hashlib
import json
import os
import posixpath
import pwd
import re
import runpy
import stat
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HOST='adlerzug.duckdns.org'
PREFIX='/demo/ki-adler-portaltest/'
PARSER_SHA='8f41cb04d1ef2babe441883d6f2aa73ff165bdd5b6653afaf236685d75fb04e8'
MAIN='/etc/nginx/nginx.conf'
STATE=Path('/var/lib/ki-adler-test-proxy')


class ProxyError(Exception):pass


def digest(data):return hashlib.sha256(data).hexdigest()


def atomic(path,data,original_stat=None):
    if path.is_symlink():raise ProxyError('Unsicherer Dateipfad')
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.ki-adler-')
    try:
        with os.fdopen(fd,'wb') as file:
            file.write(data);file.flush();os.fsync(file.fileno())
            if original_stat:
                os.fchown(file.fileno(),original_stat.st_uid,original_stat.st_gid)
                os.fchmod(file.fileno(),stat.S_IMODE(original_stat.st_mode))
            else:os.fchmod(file.fileno(),0o600)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def include_match(path,pattern):
    # Nginx glob '*' does not cross a slash. Refuse recursive patterns.
    if '**' in pattern:raise ProxyError('Rekursive Includes nicht unterstützt')
    left,right=Path(path).parts,Path(pattern).parts
    return len(left)==len(right) and all(fnmatch.fnmatchcase(a,b) for a,b in zip(left,right))


def clone_text(text,files,mapping,lexer):
    ts=lexer(text);edits=[];segment=[]
    file_directives={'ssl_certificate','ssl_certificate_key','ssl_trusted_certificate','ssl_dhparam','auth_basic_user_file'}
    for value,start,end in ts:
        if value in ('{','}'):
            segment=[];continue
        if value!=';':segment.append((value,start,end));continue
        if segment:
            name=segment[0][0]
            if name=='include':
                if len(segment)!=2:raise ProxyError('Unbekannte Include-Syntax')
                pattern=segment[1][0]
                if '$' in pattern:raise ProxyError('Dynamischer Include nicht unterstützt')
                if not pattern.startswith('/'):pattern=posixpath.join('/etc/nginx',pattern)
                pattern=posixpath.normpath(pattern)
                matches=[p for p in files if include_match(p,pattern)]
                if not matches and not any(c in pattern for c in '*?['):raise ProxyError('Include fehlt im geprüften Dump')
                replacement='\n'.join('include "'+str(mapping[p])+'";' for p in matches) or '# empty include\n'
                edits.append((segment[0][1],end,replacement))
            elif name in file_directives and len(segment)>1:
                value=segment[1][0]
                if not value.startswith('/') or '$' in value:
                    raise ProxyError('Relative oder dynamische Sicherheitsdatei muss manuell geprüft werden')
        segment=[]
    for start,end,replacement in reversed(edits):text=text[:start]+replacement+text[end:]
    return text


class Activation:
    def __init__(self,home,state,api):
        self.home=Path(home);self.state=Path(state);self.api=api

    def run(self,args):
        result=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,timeout=45)
        if result.returncode:
            atomic(self.state/'last-error.log',result.stderr[:128*1024])
            raise ProxyError('Nginx-/Dienstprüfung fehlgeschlagen; keine vertraulichen Details ausgegeben')
        return result.stdout.decode()

    def probe(self,url,banner=False):
        # Proxy bypass is solely for the explicitly local loopback health check.
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({})) if url.startswith('http://127.0.0.1:5071/') else urllib.request.build_opener()
        with opener.open(url,timeout=15) as response:
            data=response.read(1024*1024)
            if response.status!=200 or (banner and b'ISOLIERTER PORTALTEST' not in data):
                raise ProxyError('Testseite nicht sicher erreichbar')

    def mount_ready(self):
        root=self.home/'ki-adler-portaltest'
        if root.is_symlink() or (root/'private').is_symlink():raise ProxyError('Unsicherer Testpfad')
        marker=json.loads((root/'private/https-update.json').read_text())
        if marker.get('status')!='applied' or marker.get('source')!='1b25ed14325cf72906a4bfadfcd71ec56936673f':
            raise ProxyError('Geprüftes Testmount-Update fehlt')
        self.probe('http://127.0.0.1:5071'+PREFIX,banner=True)

    def candidate(self):
        dump=self.run(['nginx','-T'])
        try:files=self.api['split_dump'](dump)
        except self.api['PreviewError'] as error:raise ProxyError(str(error)) from None
        if MAIN not in files:raise ProxyError('Unbekannter Nginx-Hauptpfad')
        try:path,snapshot,unused=self.api['make_candidate'](files)
        except self.api['PreviewError'] as error:raise ProxyError(str(error)) from None
        target=Path(path).resolve(strict=True)
        if not target.is_relative_to(Path('/etc/nginx')) or not target.is_file():raise ProxyError('Ungültige Zieldatei')
        original=target.read_bytes()
        if original.decode().rstrip('\r\n')!=snapshot.rstrip('\r\n'):raise ProxyError('Aktive Site während Prüfung verändert')
        _,_,text=self.api['make_candidate']({path:original.decode()})
        candidate=text.encode()
        return files,path,target,original,candidate

    def syntax_candidate(self,files,path,candidate):
        with tempfile.TemporaryDirectory(prefix='ki-adler-nginx-check-') as folder:
            mapping={name:Path(folder)/('c'+str(i)+'.conf') for i,name in enumerate(files)}
            for name,text in files.items():
                if name==path:text=candidate.decode()
                rewritten=clone_text(text,files,mapping,self.api['tokens'])
                atomic(mapping[name],rewritten.encode())
            self.run(['nginx','-t','-c',str(mapping[MAIN])])

    def plan(self,files,path,target,original,candidate):
        return {'target':str(target),'dump_path':path,'original_sha':digest(original),'candidate_sha':digest(candidate),
                'all_configs':{p:digest(t.rstrip('\r\n').encode()) for p,t in files.items()},
                'host':HOST,'prefix':PREFIX,'applied':False}

    def check(self):
        self.mount_ready()
        self.test_links()
        files,path,target,original,candidate=self.candidate()
        self.syntax_candidate(files,path,candidate)
        proposal=self.plan(files,path,target,original,candidate)
        atomic(self.state/'candidate.conf',candidate)
        atomic(self.state/'proposal.json',json.dumps(proposal).encode())
        print('NGINX-KANDIDAT GEPRÜFT: nginx -t mit privater Kopie erfolgreich.')
        print('Testmount auf 5071 erreichbar; bestehende Regeln 5000/5057 bleiben erhalten.')
        print('NICHT aktiviert. Vor --apply ist die ausdrückliche Freigabe erforderlich.')

    def restore(self,record):
        target=Path(record['target'])
        if target.is_symlink() or not target.resolve().is_relative_to(Path('/etc/nginx')):raise ProxyError('Ungültiger Rücknahmepfad')
        current=target.read_bytes();backup=(self.state/'original-before-apply.conf').read_bytes()
        if digest(backup)!=record['original_sha'] or digest(current) not in (record['candidate_sha'],record['original_sha']):
            raise ProxyError('Site oder Sicherung fremd verändert; keine Rücknahme erzwungen')
        atomic(target,backup,target.stat())
        self.run(['nginx','-t'])
        self.run(['systemctl','reload','nginx'])
        record['applied']=False;record['pending']=False
        atomic(self.state/'applied.json',json.dumps(record).encode())

    def test_links(self):
        path=self.home/'ki-adler-portaltest/private/access.json'
        if path.is_symlink():raise ProxyError('Unsichere Testzugriffsdatei')
        paths=json.loads(path.read_text()).get('paths')
        if not isinstance(paths,list) or len(paths)!=2 or any(
            not isinstance(p,str) or not re.fullmatch(re.escape(PREFIX)+'jugend/[A-Za-z0-9_-]{24,128}',p) for p in paths):
            raise ProxyError('Die beiden künstlichen Testzugriffspfade fehlen')
        return ['https://'+HOST+p for p in paths]

    def apply(self):
        proposal=json.loads((self.state/'proposal.json').read_text())
        links=self.test_links()
        self.mount_ready()
        files,path,target,original,candidate=self.candidate()
        if self.plan(files,path,target,original,candidate)!=proposal:raise ProxyError('Konfiguration seit Vorschau verändert; --check erneut erforderlich')
        self.syntax_candidate(files,path,candidate)
        # Fixed HTTPS GETs only, no member URL or credentials in network probes.
        for url in ('https://'+HOST+'/', 'https://'+HOST+'/demo/ki-adler/'):
            self.probe(url)
        atomic(self.state/'original-before-apply.conf',original)
        record=dict(proposal);record['applied']=False;record['pending']=True;record['pending']=False
        atomic(self.state/'applied.json',json.dumps(record).encode())
        try:
            if target.read_bytes()!=original:raise ProxyError('Site unmittelbar vor Aktivierung verändert')
            atomic(target,candidate,target.stat())
            self.run(['nginx','-t'])
            self.run(['systemctl','reload','nginx'])
            self.probe('https://'+HOST+PREFIX,banner=True)
            for url in ('https://'+HOST+'/', 'https://'+HOST+'/demo/ki-adler/'):
                self.probe(url)
        except BaseException:
            try:self.restore(record)
            except BaseException:raise ProxyError('Aktivierung fehlgeschlagen; automatische Rücknahme nicht vollständig bestätigt. Root-Logs lokal prüfen') from None
            raise ProxyError('Aktivierung fehlgeschlagen; ursprüngliche Site wiederhergestellt und geladen') from None
        record['applied']=True;record['pending']=False;atomic(self.state/'applied.json',json.dumps(record).encode())
        print('HTTPS-Portaltest aktiviert. Portal 5000 und Demo 5057 weiter erreichbar.')
        for link in links:print('Künstliches Testkonto: '+link)

    def rollback(self):
        record=json.loads((self.state/'applied.json').read_text())
        if not record.get('applied') and not record.get('pending'):raise ProxyError('Keine Aktivierung für Rücknahme vorhanden')
        self.restore(record)
        print('Zusätzliche HTTPS-Testweiterleitung zurückgenommen; ursprüngliche Site geladen.')


def main():
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group()
    group.add_argument('--check',action='store_true');group.add_argument('--apply',action='store_true');group.add_argument('--rollback',action='store_true')
    args=p.parse_args();os.umask(0o077)
    try:
        if os.getuid()!=0:raise ProxyError('Für die Nginx-Prüfung mit sudo python3 starten')
        home=Path(pwd.getpwnam('pi').pw_dir)
        parser=home/'preview_test_proxy.py'
        if parser.is_symlink() or digest(parser.read_bytes())!=PARSER_SHA:raise ProxyError('Geprüfte Vorschau-Steuerung fehlt oder wurde verändert')
        api=runpy.run_path(str(parser))
        if STATE.is_symlink():raise ProxyError('Unsicherer Root-Zustandspfad')
        STATE.mkdir(mode=0o700,exist_ok=True)
        if STATE.stat().st_uid!=0 or STATE.stat().st_mode&0o077:raise ProxyError('Zustandsordner muss root gehören und privat sein')
        with (STATE/'lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            controller=Activation(home,STATE,api)
            if args.apply:controller.apply()
            elif args.rollback:controller.rollback()
            else:controller.check()
    except ProxyError as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
    except Exception:
        print('Nginx-Ablauf sicher angehalten; private Root-Protokolle lokal prüfen.',file=sys.stderr);raise SystemExit(1)


if __name__=='__main__':main()

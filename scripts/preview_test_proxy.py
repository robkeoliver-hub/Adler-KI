#!/usr/bin/env python3
"""Read nginx -T from stdin; write a PRIVATE candidate. Never applies/reloads."""
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HOST='adlerzug.duckdns.org'
PREFIX='/demo/ki-adler-portaltest/'
BLOCK='''
    # BEGIN KI-ADLER PORTALTEST (isolated synthetic data on 5071)
    location = /demo/ki-adler-portaltest {
        return 308 /demo/ki-adler-portaltest/;
    }
    location ^~ /demo/ki-adler-portaltest/ {
        proxy_pass http://127.0.0.1:5071;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_no_cache 1;
        proxy_cache_bypass 1;
        access_log off;
    }
    # END KI-ADLER PORTALTEST
'''


class PreviewError(Exception):pass


def tokens(text):
    """Small conservative nginx lexer: comments/quotes do not open blocks."""
    result=[];i=0
    while i<len(text):
        if text[i].isspace():i+=1;continue
        if text[i]=='#':
            end=text.find('\n',i);i=len(text) if end<0 else end+1;continue
        start=i
        if text[i] in '{};':
            result.append((text[i],start,i+1));i+=1;continue
        value=[];quote=None
        while i<len(text):
            c=text[i]
            if c=='\\':
                if i+1>=len(text):raise PreviewError('Unvollständiges Escape')
                value.append(text[i+1]);i+=2;continue
            if quote:
                if c==quote:quote=None
                else:value.append(c)
                i+=1;continue
            if c in '\"\'':quote=c;i+=1;continue
            if c=='$' and i+1<len(text) and text[i+1]=='{':
                end=text.find('}',i+2)
                if end<0:raise PreviewError('Unvollständige Variable')
                value.append(text[i:end+1]);i=end+1;continue
            if c.isspace() or c in '{};#':break
            value.append(c);i+=1
        if quote:raise PreviewError('Nicht unterstützte Syntax')
        result.append((''.join(value),start,i))
    return result


def blocks(text):
    root={'header':[],'children':[],'directives':[]};stack=[root];pending=[]
    for value,start,end in tokens(text):
        if value=='{':
            if not pending:raise PreviewError('Block ohne Namen')
            node={'header':pending,'children':[],'directives':[],'open':start}
            stack[-1]['children'].append(node);stack.append(node);pending=[]
        elif value=='}':
            if pending or len(stack)==1:raise PreviewError('Unvollständiger Block')
            stack[-1]['close']=start;stack.pop()
        elif value==';':
            if not pending:raise PreviewError('Leere Direktive')
            stack[-1]['directives'].append(pending);pending=[]
        else:pending.append(value)
    if len(stack)!=1 or pending:raise PreviewError('Unvollständige Konfiguration')
    return root


def all_blocks(node):
    for child in node['children']:
        yield child
        yield from all_blocks(child)


def split_dump(text):
    matches=list(re.finditer(r'(?m)^# configuration file (/[^\r\n]+):\s*$',text))
    if not matches:raise PreviewError('Kein vollständiger nginx -T Dump empfangen')
    files={}
    for i,match in enumerate(matches):
        path=match.group(1)
        if path in files:raise PreviewError('Doppelter Konfigurationspfad')
        files[path]=text[match.end():matches[i+1].start() if i+1<len(matches) else len(text)].lstrip('\r\n')
    return files


def make_candidate(files):
    candidates=[]
    for path,text in files.items():
        # Fail closed on unresolved includes for the target server's direct
        # routing. Do not guess upstream topology from a screenshot.
        tree=blocks(text)
        for node in all_blocks(tree):
            if node['header']!=['server']:continue
            names=[d[1:] for d in node['directives'] if d[0]=='server_name']
            listens=[d[1:] for d in node['directives'] if d[0]=='listen']
            if not any(HOST in n for n in names):continue
            if not any('ssl' in d and any(v=='443' or v.endswith(':443') for v in d) for d in listens):continue
            locs=[x for x in node['children'] if x['header'][0]=='location']
            if any(PREFIX.rstrip('/') in ' '.join(x['header']) for x in locs):
                raise PreviewError('Testlocation existiert bereits; keine doppelte Regel')
            def target(location):
                return [d[1] for d in location['directives'] if d[0]=='proxy_pass' and len(d)==2]
            if not any(x['header']==['location','^~','/demo/ki-adler/'] and target(x)==['http://127.0.0.1:5057'] for x in locs):
                raise PreviewError('Bestehende KI-Weiterleitung nicht eindeutig bestätigt')
            if not any(x['header']==['location','/'] and target(x) in (['http://127.0.0.1:5000'],['http://127.0.0.1:5000/']) for x in locs):
                raise PreviewError('Bestehende Portalweiterleitung nicht eindeutig bestätigt')
            if any(d[0]=='include' for d in node['directives']):
                raise PreviewError('Zusätzliche Server-Includes müssen zuerst geprüft werden')
            candidates.append((path,text,node))
    if len(candidates)!=1:raise PreviewError('HTTPS-Zielserver nicht eindeutig gefunden')
    path,text,node=candidates[0];point=node['close']
    candidate=text[:point]+BLOCK+text[point:]
    blocks(candidate)
    if candidate.replace(BLOCK,'',1)!=text:raise PreviewError('Bestehende Konfiguration verändert')
    return path,text,candidate


def write_private(path,data):
    if path.is_symlink():raise PreviewError('Unsicherer Ausgabepfad')
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.preview-')
    try:
        with os.fdopen(fd,'w') as file:file.write(data);file.flush();os.fsync(file.fileno())
        os.chmod(tmp,0o600);os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def read_snapshot(selected, original):
    # nginx -T already read this site with the operator's sudo rights. Preview
    # needs no extra file permissions; a dump snapshot is never a restore backup.
    try:
        disk = selected.read_text()
    except PermissionError:
        return original, False
    if disk.rstrip('\r\n') != original.rstrip('\r\n'):
        raise PreviewError('Datei seit nginx -T verändert oder nicht eindeutig')
    return disk, True


def main():
    os.umask(0o077)
    phase='Nginx-Ausgabe lesen'
    try:
        text=sys.stdin.read(2*1024*1024+1)
        if len(text)>2*1024*1024:raise PreviewError('Konfiguration zu groß')
        phase='HTTPS-Server bestimmen'
        path,original,candidate=make_candidate(split_dump(text))
        phase='Zielpfad prüfen'
        selected=Path(path)
        if not selected.resolve().is_relative_to(Path('/etc/nginx')):
            raise PreviewError('Zieldatei liegt außerhalb /etc/nginx')
        # nginx -T inserts blank separators. Compare exact current bytes after
        # trimming only trailing newlines; never overwrite the live file.
        phase='Site-Snapshot prüfen'
        disk,verified=read_snapshot(selected,original)
        # Build preview from verified disk bytes or the privileged nginx -T snapshot.
        # Applying later always requires a fresh privileged backup/hash check.
        _,_,candidate=make_candidate({path:disk})
        phase='Privaten Testordner prüfen'
        root=Path.home()/'ki-adler-portaltest'
        if root.is_symlink() or (root/'private').is_symlink() or not (root/'private/state.json').is_file():
            raise PreviewError('Vorbereiteter Portaltest fehlt')
        out=root/'private/proxy-preview'
        if out.is_symlink():raise PreviewError('Unsicherer Vorschauordner')
        out.mkdir(mode=0o700,exist_ok=True)
        if out.stat().st_mode&0o077:raise PreviewError('Vorschauordner nicht privat')
        phase='Private Vorschau speichern'
        write_private(out/'candidate.conf',candidate)
        write_private(out/'snapshot.conf',disk)
        report={'target':str(selected.resolve()),'snapshot_sha256':hashlib.sha256(disk.encode()).hexdigest(),
                'snapshot_disk_verified':verified,'restorable_backup':False,
                'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
                'host':HOST,'prefix':PREFIX,'test_port':5071,'applied':False,
                'requires_mounted_test_and_nginx_validation':True}
        write_private(out/'report.json',json.dumps(report,indent=2))
        print('VORSCHAU BEREIT: genau ein HTTPS-Server bestätigt.')
        if not verified:print('Site nur über nginx -T lesbar: Snapshot gespeichert, kein Wiederherstellungsbackup.')
        print('Bestehendes Portal 5000 und KI-Demo 5057 bleiben unverändert.')
        print('Vorgesehener neuer Pfad: https://'+HOST+PREFIX)
        print('Vorschau nur privat gespeichert. Noch NICHT aktiviert; kein Nginx-Reload.')
        print('Vor Freigabe: isolierten Test auf Präfix/Cookie-Namen umstellen und nginx -t prüfen.')
    except (PreviewError,OSError,ValueError) as error:
        if isinstance(error,PreviewError):message=str(error)
        elif isinstance(error,OSError):
            reason={1:'Zugriff verweigert',2:'Datei fehlt',13:'Zugriff verweigert',28:'Speicher voll',30:'Dateisystem schreibgeschützt'}.get(error.errno,'Dateizugriff fehlgeschlagen')
            message='Vorschau angehalten: '+phase+' – '+reason
        else:message='Vorschau angehalten: '+phase+' – Datenformat nicht unterstützt'
        print(message,file=sys.stderr);raise SystemExit(1)


if __name__=='__main__':main()

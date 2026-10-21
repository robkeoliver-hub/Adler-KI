#!/usr/bin/env python3
"""Move the test-only Adler button above the existing bottom navigation."""
import argparse
import hashlib
import json
import os
import pwd
import tempfile
from pathlib import Path

KEY='portal/portal_adler/static/panel.css'
OLD='3d5ec1dfe311ed199629addbd74e10c3c8d877b98d79b6e7e9da6db2d3a9789f'
NEW='8882f9fa217dbbabc1a42a4df548f4f87564825d25b9b094aaab1e7a977d12ad'


class FixError(Exception):pass


def sha(data):return hashlib.sha256(data).hexdigest()


def write(path,data):
    if path.is_symlink():raise FixError('Unsicherer Dateipfad')
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.adler-css-')
    try:
        with os.fdopen(fd,'wb') as file:file.write(data);file.flush();os.fsync(file.fileno())
        os.chmod(tmp,0o600);os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def fix(home,rollback=False):
    root=Path(home).resolve()/'ki-adler-portaltest'
    css=root/KEY;manifest=root/'private/code-hashes.json';backup=root/'private/adler-button-css-backup-v1'
    for path in (root,css,manifest,backup):
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise FixError('Unsicherer Testpfad')
    current=css.read_bytes();raw=manifest.read_bytes();hashes=json.loads(raw)
    if rollback:
        original=(backup/'panel.css').read_bytes();saved=(backup/'code-hashes.json').read_bytes();before=json.loads(saved)
        if sha(original)!=OLD or before.get(KEY)!=OLD:raise FixError('Sicherung ungültig')
        expected=dict(before);expected[KEY]=hashes.get(KEY)
        if hashes!=expected or hashes.get(KEY) not in (OLD,NEW) or sha(current) not in (OLD,NEW):
            raise FixError('Weitere Änderungen vorhanden; keine Rücknahme erzwungen')
        write(css,original);write(manifest,saved)
        print('Vorherige Position wiederhergestellt. Dienste und Nginx unverändert.');return
    if sha(current)==NEW and hashes.get(KEY)==NEW:
        print('Adler-Schaltfläche ist bereits korrigiert. Seite in Safari neu laden.');return
    if sha(current)!=OLD or hashes.get(KEY)!=OLD:raise FixError('Stylesheet entspricht nicht dem geprüften Ausgangsstand')
    changed=current.replace(b'bottom:calc(12px + env(safe-area-inset-bottom))',b'bottom:calc(100px + env(safe-area-inset-bottom))')
    if sha(changed)!=NEW:raise FixError('Unerwartete CSS-Struktur')
    if backup.exists():raise FixError('Sicherung existiert bereits; nichts überschrieben')
    backup.mkdir(mode=0o700)
    write(backup/'panel.css',current);write(backup/'code-hashes.json',raw)
    hashes[KEY]=NEW
    try:
        write(css,changed);write(manifest,json.dumps(hashes).encode())
    except BaseException:
        write(css,current);write(manifest,raw)
        raise
    print('Adler-Schaltfläche oberhalb der Menüleiste positioniert. Jetzt die Testseite in Safari neu laden.')
    print('Kein Neustart, keine Nginx-Änderung und keine Datenbankänderung.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rollback',action='store_true');args=parser.parse_args()
    os.umask(0o077)
    try:
        account=pwd.getpwuid(os.getuid())
        if account.pw_name!='pi' or os.getuid()==0:raise FixError('Als pi ausführen, ohne sudo')
        fix(account.pw_dir,args.rollback)
    except FixError as error:
        print(str(error));raise SystemExit(1)
    except Exception:
        print('CSS-Korrektur angehalten. Keine Dienst- oder Nginx-Änderung.');raise SystemExit(1)


if __name__=='__main__':main()

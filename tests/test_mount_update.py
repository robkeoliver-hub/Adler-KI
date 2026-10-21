"""Update/rollback use synthetic local files and SQLite only."""
import hashlib
import importlib.util
import io
import json
import runpy
import sqlite3
import zipfile
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mount_update',ROOT/'scripts/update_test_mount.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


@pytest.fixture
def update(tmp_path,monkeypatch):
    files={'scripts/prepare_portal_test.py':(ROOT/'scripts/prepare_portal_test.py').read_bytes()}
    files.update({name:(ROOT/name).read_bytes() for name in m.ASSETS})
    (tmp_path/'prepare_portal_test.py').write_bytes(files['scripts/prepare_portal_test.py'])
    api=runpy.run_path(str(tmp_path/'prepare_portal_test.py'))
    root=tmp_path/'ki-adler-portaltest';(root/'private').mkdir(parents=True)
    old={}
    for name in m.OLD:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'synthetic old '+name.encode());old[name]=m.sha(p.read_bytes())
    monkeypatch.setattr(m,'OLD',old)
    (root/'runner.py').write_text(api['RUNNER'])
    hashes={name:m.sha((root/name).read_bytes()) for name in [*old,'runner.py']}
    (root/'private/code-hashes.json').write_text(json.dumps(hashes))
    (root/'private/state.json').write_text(json.dumps({'source':api['SOURCE_COMMIT'],'export':api['EXPORT_HASH'],'ready':True}))
    (root/'private/access.json').write_text(json.dumps({'paths':['/jugend/'+'A'*32,'/jugend/'+'B'*32]}))
    with sqlite3.connect(root/'portal/schuetzenjugend.db') as db:
        db.execute('create table synthetic (value text)');db.execute('insert into synthetic values (?)',('keep',))
    for name in ('schuetzenjugend','ki-adler-test','ki-adler'):
        d=tmp_path/name;d.mkdir();(d/'keep').write_text('untouched')
    u=m.Updater(tmp_path,files);active=[True];calls=[]
    def start():u.stage.validate();active[0]=True;calls.append('start')
    def stop():active[0]=False;calls.append('stop')
    monkeypatch.setattr(u.stage,'start',start);monkeypatch.setattr(u.stage,'stop',stop)
    monkeypatch.setitem(u.api,'port_open',lambda:False)
    monkeypatch.setattr(u.stage,'run',lambda args,**kwargs:calls.append('selftest'))
    return u,root,active,calls


def test_apply_preserves_existing_data_and_is_repeatable(update):
    u,root,active,calls=update
    u.apply()
    assert active[0] and calls==['stop','selftest','start']
    assert 'serve(application,' in (root/'runner.py').read_text()
    assert (root/'portal/portal_adler/testing_mount.py').exists()
    assert json.loads((root/'private/https-update.json').read_text())['status']=='applied'
    assert all(p.startswith(m.PREFIX+'/jugend/') for p in json.loads((root/'private/access.json').read_text())['paths'])
    with sqlite3.connect(root/'portal/schuetzenjugend.db') as db:assert db.execute('select value from synthetic').fetchone()[0]=='keep'
    before=(u.backup/'manifest.json').read_bytes();u.apply()
    assert (u.backup/'manifest.json').read_bytes()==before and calls.count('stop')==1
    for name in ('schuetzenjugend','ki-adler-test','ki-adler'):assert (u.home/name/'keep').read_text()=='untouched'


def test_rollback_restores_code_access_and_database(update):
    u,root,active,calls=update
    original=(root/'runner.py').read_bytes();access=(root/'private/access.json').read_bytes()
    u.apply()
    with sqlite3.connect(root/'portal/schuetzenjugend.db') as db:db.execute('delete from synthetic')
    u.restore()
    assert active[0] and (root/'runner.py').read_bytes()==original
    assert (root/'private/access.json').read_bytes()==access
    assert not (root/'portal/portal_adler/testing_mount.py').exists()
    with sqlite3.connect(root/'portal/schuetzenjugend.db') as db:assert db.execute('select value from synthetic').fetchone()[0]=='keep'


def test_failed_new_selftest_restores_old_instance(update,monkeypatch):
    u,root,active,calls=update;before=(root/'runner.py').read_bytes()
    def fail(*args,**kwargs):raise RuntimeError('synthetic failure')
    monkeypatch.setattr(u.stage,'run',fail)
    with pytest.raises(m.UpdateError):u.apply()
    assert active[0] and (root/'runner.py').read_bytes()==before
    assert json.loads(u.marker.read_text())['status']=='rolled_back'


def test_unexpected_asset_aborts_before_stopping(update):
    u,root,active,calls=update;(root/'portal/portal_adler/static/panel.js').write_text('unexpected')
    with pytest.raises(Exception):u.apply()
    assert active[0] and not calls


def test_modified_controller_is_never_executed(update):
    u,root,active,calls=update;(u.home/'prepare_portal_test.py').write_text('raise RuntimeError("must not execute")')
    with pytest.raises(m.UpdateError):m.Updater(u.home,u.files)


def test_corrupt_backup_aborts_before_stop(update):
    u,root,active,calls=update;u.apply();calls.clear();(u.backup/'synthetic.db').write_bytes(b'changed')
    with pytest.raises(m.UpdateError):u.restore()
    assert active[0] and not calls


def test_outside_paths_are_rejected(update):
    u,root,*_=update
    with pytest.raises(m.UpdateError):u.safe('../schuetzenjugend/app.py')


def test_busy_port_never_mutates_code(update,monkeypatch):
    u,root,active,calls=update;before=(root/'runner.py').read_bytes()
    monkeypatch.setitem(u.api,'port_open',lambda:True)
    with pytest.raises(m.UpdateError):u.apply()
    assert (root/'runner.py').read_bytes()==before and not u.backup.exists()


def test_runner_rewrite_is_explicit_and_compilable():
    api=runpy.run_path(str(ROOT/'scripts/prepare_portal_test.py'))
    rewritten=m.runner(api['RUNNER']);compile(rewritten,'test-runner','exec')
    assert b'ADLER_ISOLATED_TEST' in rewritten and b'Client(application,Response)' in rewritten
    with pytest.raises(m.UpdateError):m.runner('unexpected')


def test_pinned_archive_and_unlisted_files(monkeypatch):
    files={'asset.py':b'synthetic'}
    manifest=''.join(m.sha(v)+'  '+k+'\n' for k,v in files.items()).encode()
    monkeypatch.setattr(m,'MANIFEST',m.sha(manifest))
    def archive(extra):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            for name,data in {**files,'SHA256SUMS':manifest,**extra}.items():z.writestr('root/'+name,data)
        return out.getvalue()
    assert m.payload(archive({}))['asset.py']==b'synthetic'
    with pytest.raises(m.UpdateError):m.payload(archive({'unlisted.py':b'no'}))
    with pytest.raises(m.UpdateError):m.payload(archive({'../escape.py':b'no'}))

"""Synthetic installer regression: existing stage only, atomic recovery, no live Pi."""
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
spec=importlib.util.spec_from_file_location('companion_update',ROOT/'scripts/update_companion.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


@pytest.fixture
def update(tmp_path,monkeypatch):
    files={name:(ROOT/name).read_bytes() for name in m.PACKAGE_HASHES}
    (tmp_path/'prepare_portal_test.py').write_bytes((ROOT/'scripts/prepare_portal_test.py').read_bytes())
    root=tmp_path/'ki-adler-portaltest';(root/'private').mkdir(parents=True)
    hashes={}
    for name in m.OLD_PACKAGE_HASHES:
        raw=b'synthetic old '+name.encode();path=root/'portal'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        hashes['portal/'+name]=m.sha(raw)
    monkeypatch.setattr(m,'OLD_PACKAGE_HASHES',{name:[hashes['portal/'+name]] for name in m.OLD_PACKAGE_HASHES})
    runner=(ROOT/'tests/fixtures/runner-pr10.txt').read_bytes();(root/'runner.py').write_bytes(runner);hashes['runner.py']=m.sha(runner)
    (root/'private/code-hashes.json').write_text(json.dumps(hashes))
    api=runpy.run_path(str(tmp_path/'prepare_portal_test.py'))
    (root/'private/state.json').write_text(json.dumps({'source':api['SOURCE_COMMIT'],'export':api['EXPORT_HASH'],'ready':True}))
    with sqlite3.connect(root/'portal/schuetzenjugend.db') as db:
        db.execute('create table synthetic (value text)');db.execute('insert into synthetic values (?)',('keep',))
    for dirname in ('schuetzenjugend','ki-adler-test'):
        d=tmp_path/dirname;d.mkdir();(d/'unchanged').write_text('untouched')
    u=m.Updater(tmp_path,files);calls=[]
    monkeypatch.setattr(u.stage,'stop',lambda:calls.append('stop'))
    monkeypatch.setattr(u.stage,'start',lambda:(u.stage.validate(),calls.append('start')))
    monkeypatch.setattr(u.stage,'run',lambda *a,**kw:calls.append('test'))
    monkeypatch.setitem(u.api,'port_open',lambda:False)
    return u,root,calls


def test_apply_repeat_and_offline_rollback(update):
    u,root,calls=update;original=(root/'runner.py').read_bytes();u.apply()
    assert calls==['stop','test','start'] and 'portal_adler.chat' in (root/'runner.py').read_text()
    assert not json.loads((root/'private/dialogue.json').read_text())['ADLER_DIALOGUE_APPROVED']
    saved=(u.backup/'manifest.json').read_bytes();u.apply();assert (u.backup/'manifest.json').read_bytes()==saved
    u.restore();assert (root/'runner.py').read_bytes()==original
    assert not (root/'portal/portal_adler/dialogue.py').exists()
    assert not (root/'private/dialogue.json').exists()
    with sqlite3.connect(root/'portal/schuetzenjugend.db') as db:assert db.execute('select value from synthetic').fetchone()[0]=='keep'
    for d in ('schuetzenjugend','ki-adler-test'):assert (u.home/d/'unchanged').read_text()=='untouched'


def test_failed_selftest_recovers_previous_test(update,monkeypatch):
    u,root,calls=update;before=(root/'runner.py').read_bytes()
    monkeypatch.setattr(u.stage,'run',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('synthetic failure')))
    with pytest.raises(m.UpdateError):u.apply()
    assert (root/'runner.py').read_bytes()==before and calls[-1]=='start'
    assert json.loads(u.marker.read_text())['status']=='rolled_back'


def test_no_overwrite_of_existing_provider_credentials(update):
    u,root,calls=update;(root/'private/dialogue.json').write_text('PRIVATE-TEST-VALUE')
    with pytest.raises(m.UpdateError):u.apply()
    assert not calls and (root/'private/dialogue.json').read_text()=='PRIVATE-TEST-VALUE'


def test_no_killing_unrelated_port_listener(update,monkeypatch):
    u,root,calls=update;before=(root/'runner.py').read_bytes()
    monkeypatch.setitem(u.api,'port_open',lambda:True)
    with pytest.raises(m.UpdateError):u.apply()
    assert (root/'runner.py').read_bytes()==before and not u.backup.exists()


def test_changed_code_blocks_update_and_later_change_blocks_rollback(update):
    u,root,calls=update;path=root/'portal/portal_adler/static/panel.css';original=path.read_bytes();path.write_text('unexpected')
    with pytest.raises(Exception):u.apply()
    assert not calls
    path.write_bytes(original);u.apply();path.write_text('later edit')
    with pytest.raises(m.UpdateError):u.restore()
    assert path.read_text()=='later edit'


def test_runner_and_source_limits():
    raw=(ROOT/'tests/fixtures/runner-pr10.txt').read_bytes()
    compiled=m.patched_runner(raw);assert b'load_private_settings' in compiled
    with pytest.raises(m.UpdateError):m.patched_runner(raw+b'\n')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for name in m.PACKAGE_HASHES:z.writestr('source/'+name,(ROOT/name).read_bytes())
    assert set(m.unpack(buf.getvalue()))==set(m.PACKAGE_HASHES)
    for name,data in [('source/../evil',b'x'),('source/a',b'x')]:
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr(name,data)
        with pytest.raises(m.UpdateError):m.unpack(buf.getvalue())

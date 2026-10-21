"""Synthetic archive/install safety checks. No real club files or services."""
import hashlib
import importlib.util
import io
import json
import os
import stat
import zipfile
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('portal_staging',Path(__file__).resolve().parents[1]/'scripts/prepare_portal_test.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def archive(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for p,data in files.items():z.writestr('root/'+p,data)
    return out.getvalue()


def source(monkeypatch, files=None):
    files=files or {'portal_adler/__init__.py':b'# synthetic source\n'}
    manifest=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n' for k,v in files.items()).encode()
    monkeypatch.setattr(m,'SOURCE_MANIFEST',hashlib.sha256(manifest).hexdigest())
    return archive({**files,'SHA256SUMS':manifest})


def export(monkeypatch, extra=None):
    files={'app.py':b'# synthetic only\n', 'meyton_ocr.py':b'# no imports\n',
           'templates/base.html':b"<body><nav>Keep</nav><script>navigator.serviceWorker.register('/service-worker.js')</script></body>"}
    files.update(extra or {})
    raw=archive(files);monkeypatch.setattr(m,'EXPORT_HASH',hashlib.sha256(raw).hexdigest())
    return raw


@pytest.mark.parametrize('name',['../app.py','/root/app.py','root/../../app.py','root/C:/app.py','root/a\\b.py'])
def test_unsafe_zip_paths(name):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:z.writestr(name,b'')
    with pytest.raises(m.StageError):m.zip_files(out.getvalue())


def test_zip_links_and_case_duplicates_rejected():
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        i=zipfile.ZipInfo('root/link.py');i.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(i,'/etc/passwd')
    with pytest.raises(m.StageError):m.zip_files(out.getvalue())
    raw=archive({'App.py':b'','app.py':b''})
    with pytest.raises(m.StageError):m.zip_files(raw)


def test_source_pin_and_manifest_reject_tampering(monkeypatch):
    raw=source(monkeypatch)
    assert 'portal_adler/__init__.py' in m.source_payload(raw)
    files=m.zip_files(raw);files['portal_adler/__init__.py']=b'changed'
    with pytest.raises(m.StageError):m.source_payload(archive(files))
    files=m.zip_files(raw);files['unlisted.py']=b'extra'
    with pytest.raises(m.StageError):m.source_payload(archive(files))
    monkeypatch.setattr(m,'SOURCE_MANIFEST','0'*64)
    with pytest.raises(m.StageError):m.source_payload(raw)


@pytest.mark.parametrize('entry,data', [('club.db',b'db'),('uploads/a.py',b''),('hidden.py',b'SQLite format 3\x00')])
def test_private_export_files_rejected_even_when_hash_matches(monkeypatch,entry,data):
    raw=export(monkeypatch,{entry:data})
    with pytest.raises(m.StageError):m.export_payload(raw)


def test_unknown_export_rejected_before_any_directory(tmp_path,monkeypatch):
    path=tmp_path/'export.zip';path.write_bytes(b'not reviewed')
    stage=m.Stage(tmp_path)
    with pytest.raises(m.StageError):stage.prepare(path)
    assert not stage.root.exists()


def test_prepare_never_overwrites_or_touches_live_directories(tmp_path,monkeypatch):
    raw=export(monkeypatch);src=source(monkeypatch);path=tmp_path/'export.zip';path.write_bytes(raw)
    for name in ('schuetzenjugend','ki-adler-test'):
        folder=tmp_path/name;folder.mkdir();(folder/'untouched').write_text('original')
    stage=m.Stage(tmp_path);calls=[]
    monkeypatch.setattr(m,'port_open',lambda:False)
    monkeypatch.setattr(stage,'run',lambda args,**kwargs:calls.append(args))
    stage.prepare(path,src)
    for name in ('schuetzenjugend','ki-adler-test'):assert (tmp_path/name/'untouched').read_text()=='original'
    assert path.read_bytes()==raw
    assert any(x[-1]=='selftest' for x in calls)
    assert any('-m' in x and 'venv' in x for x in calls)
    assert all('sudo' not in x and 'systemctl' not in x and 'nginx' not in x for x in calls)
    config=json.loads(stage.config.read_text());assert len(config['tokens'])==2 and config['tokens'][0]!=config['tokens'][1]
    assert stage.config.stat().st_mode&0o777==0o600
    assert stage.root.stat().st_mode&0o777==0o700
    base=(stage.root/'portal/templates/base.html').read_text()
    assert '<nav>Keep</nav>' in base and 'ISOLIERTER PORTALTEST' in base
    assert "navigator.serviceWorker.register('/service-worker.js')" not in base
    assert '{{ ki_adler_panel() }}' in base
    stage.validate()
    with pytest.raises(m.StageError):stage.prepare(path,src)
    (stage.root/'portal/app.py').write_text('# changed')
    with pytest.raises(m.StageError):stage.validate()


def test_failed_selftest_leaves_unready_state(tmp_path,monkeypatch):
    raw=export(monkeypatch);src=source(monkeypatch);path=tmp_path/'export.zip';path.write_bytes(raw)
    stage=m.Stage(tmp_path);monkeypatch.setattr(m,'port_open',lambda:False)
    def fail(args,**kwargs):
        if args[-1]=='selftest':raise m.StageError('synthetic test failure')
    monkeypatch.setattr(stage,'run',fail)
    with pytest.raises(m.StageError):stage.prepare(path,src)
    assert not json.loads((stage.root/'private/state.json').read_text())['ready']
    with pytest.raises(m.StageError):stage.validate()


def test_busy_port_refuses_before_install(tmp_path,monkeypatch):
    raw=export(monkeypatch);path=tmp_path/'export.zip';path.write_bytes(raw)
    stage=m.Stage(tmp_path);monkeypatch.setattr(m,'port_open',lambda:True)
    with pytest.raises(m.StageError):stage.prepare(path,source(monkeypatch))
    assert not stage.root.exists()


def test_private_write_does_not_follow_symlink(tmp_path):
    original=tmp_path/'original';original.write_text('keep')
    link=tmp_path/'link';link.symlink_to(original)
    with pytest.raises(m.StageError):m.private_write(link,'change')
    assert original.read_text()=='keep'


def test_stop_uses_verified_pidfd_only(tmp_path,monkeypatch):
    stage=m.Stage(tmp_path);private=stage.root/'private';private.mkdir(parents=True)
    state={'pid':99999,'start':'synthetic'};states=iter([state,state,None]);sent=[]
    monkeypatch.setattr(stage,'process',lambda:next(states))
    monkeypatch.setattr(m.os,'pidfd_open',lambda pid:7)
    monkeypatch.setattr(m.os,'close',lambda fd:None)
    monkeypatch.setattr(m.signal,'pidfd_send_signal',lambda fd,sig:sent.append((fd,sig)))
    stage.stop()
    assert sent==[(7,m.signal.SIGTERM)]


def test_process_mismatch_never_signals(tmp_path,monkeypatch):
    stage=m.Stage(tmp_path);states=iter([{'pid':99999,'start':'one'},{'pid':99999,'start':'two'}]);sent=[]
    monkeypatch.setattr(stage,'process',lambda:next(states));monkeypatch.setattr(m.os,'pidfd_open',lambda pid:7)
    monkeypatch.setattr(m.os,'close',lambda fd:None);monkeypatch.setattr(m.signal,'pidfd_send_signal',lambda *args:sent.append(args))
    with pytest.raises(m.StageError):stage.stop()
    assert not sent


def test_runner_and_installer_do_not_select_live_port():
    assert 'port=5071' in m.RUNNER and 'host=\'127.0.0.1\'' in m.RUNNER
    assert 'os.environ.clear()' in m.RUNNER
    assert 'synthetic_only' in m.RUNNER and 'read_only_test' in m.RUNNER
    assert m.PORT not in (5000,5057,5059)

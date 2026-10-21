"""Installer tests use temporary dirs, synthetic configs and mocked systemd/proc."""
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location('pi_installer', Path(__file__).resolve().parents[1] / 'scripts/install_pi.py')
m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def archive(monkeypatch, extra=None):
    source = b'print("synthetic")\n'
    manifest = (hashlib.sha256(source).hexdigest() + '  run.py\n').encode()
    monkeypatch.setattr(m, 'MANIFEST_HASH', hashlib.sha256(manifest).hexdigest())
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('root/run.py', source);z.writestr('root/SHA256SUMS', manifest)
        if extra:z.writestr(*extra)
    return out.getvalue()


def test_source_exact_manifest_and_reject_extra_or_traversal(monkeypatch):
    assert m.checked_payload(archive(monkeypatch))['run.py'].startswith(b'print')
    for extra in [('root/config.ini', 'synthetic-secret'), ('root/../evil.py', '')]:
        with pytest.raises(m.InstallError):m.checked_payload(archive(monkeypatch, extra))


def test_wrong_source_hash_refuses_execution(monkeypatch):
    raw = archive(monkeypatch);monkeypatch.setattr(m, 'MANIFEST_HASH', '0' * 64)
    with pytest.raises(m.InstallError):m.checked_payload(raw)


def test_private_write_atomic_permissions_and_no_symlink(tmp_path):
    target = tmp_path / 'secret.ini';m.private_write(target, 'synthetic-only')
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    m.private_write(target, 'replaced');assert target.read_text() == 'replaced'
    link = tmp_path / 'link';link.symlink_to(target)
    with pytest.raises(m.InstallError):m.private_write(link, 'bad')
    assert target.read_text() == 'replaced'


def test_backup_preserves_config_without_venv_and_never_modifies_old(tmp_path):
    old = tmp_path / 'old';old.mkdir();(old/'run.py').write_text('synthetic-code')
    (old/'config.ini').write_text('synthetic-private-config')
    (old/'.venv').mkdir();(old/'.venv/placeholder').write_text('left-in-place')
    target = tmp_path / 'backup.tar.gz'
    launch = {'argv':['.venv/bin/python','run.py'],'env':{'SYNTHETIC':'PRIVATE-PLACEHOLDER'}}
    before = (old/'run.py').read_bytes()
    m.backup_old(old,target,launch,'effective-placeholder')
    with tarfile.open(target) as z:
        assert 'old-code/config.ini' in z.getnames()
        assert not any('.venv' in n for n in z.getnames())
        assert json.load(z.extractfile('rollback-launch.json')) == launch
    assert stat.S_IMODE(target.stat().st_mode)==0o600
    assert (old/'run.py').read_bytes()==before and (old/'.venv/placeholder').exists()
    with pytest.raises(FileExistsError):m.backup_old(old,target,launch,'')


def test_backup_rejects_symlink(tmp_path):
    old=tmp_path/'old';old.mkdir();(old/'bad').symlink_to('/etc/passwd')
    with pytest.raises(m.InstallError):m.backup_old(old,tmp_path/'backup.tar.gz',{},'')


def test_config_env_transfer_without_output_and_reject_invalid(tmp_path,capsys):
    path=tmp_path/'config.ini';path.write_text('[adler]\ndemo_code = synthetic-long-test-code\npublic_origin = https://demo.example\n')
    text,origin=m.merged_config(path,{'ADLER_API_KEY':'synthetic-private-placeholder'})
    assert 'synthetic-private-placeholder' in text and origin=='https://demo.example'
    assert capsys.readouterr().out==''
    with pytest.raises(m.InstallError):m.merged_config(path,{'ADLER_PUBLIC_ORIGIN':'http://outside.example'})


@pytest.mark.parametrize('port',[5000,80,5058,0])
def test_unit_cannot_target_portal_or_other_ports(tmp_path,port):
    with pytest.raises(m.InstallError):m.unit_text(tmp_path/'release',port,tmp_path/'candidate.env')


def test_unit_has_only_own_service_and_test_secrets_outside_unit(tmp_path):
    text=m.unit_text(tmp_path/'release',5059,tmp_path/'candidate.env')
    assert 'User=pi' in text and 'ADLER_PORT=5059' in text
    assert 'ADLER_PROVIDER=mock' in text and 'ADLER_EXTERNAL_APPROVED=false' in text
    assert 'ADLER_MODE=demo' in text and 'EnvironmentFile=' in text
    active=m.unit_text(tmp_path/'release',5057,tmp_path/'candidate.env')
    assert 'EnvironmentFile=' not in active and '5000' not in active
    assert 'schuetzenjugend' not in active and 'nginx' not in active


def fake_proc(tmp_path,monkeypatch,kind='ok'):
    old=tmp_path/'old';(old/'.venv/bin').mkdir(parents=True)
    (old/'run.py').write_text('# synthetic')
    (old/'.venv/bin/python').symlink_to(sys.executable)
    root=tmp_path/'proc';proc=root/'1234';proc.mkdir(parents=True)
    (proc/'cwd').symlink_to(old if kind!='cwd' else tmp_path)
    argv=[str(old/'.venv/bin/python'),'run.py'] if kind!='argv' else ['bad','-u','run.py']
    (proc/'cmdline').write_bytes(b'\0'.join(a.encode() for a in argv)+b'\0')
    (proc/'cgroup').write_text('0::/unit.service' if kind=='managed' else '0::/session.scope')
    (proc/'stat').write_text('1234 (python) S '+' '.join(['0']*18)+' 98765 0')
    (proc/'environ').write_bytes(b'SYNTHETIC=placeholder\0')
    real=Path;monkeypatch.setattr(m,'Path',lambda *a:root if a==('/proc',) else real(*a))
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=b'users:(("python",pid=1234,fd=3))',returncode=0))
    return old


def test_discover_exact_old_pid_not_historical_pid(tmp_path,monkeypatch):
    old=fake_proc(tmp_path,monkeypatch)
    info=m.discover_old(old)
    assert info['pid']==1234 and info['start']=='98765' and info['env']=={'SYNTHETIC':'placeholder'}


@pytest.mark.parametrize('kind',['cwd','argv','managed'])
def test_discover_refuses_foreign_or_managed_process(tmp_path,monkeypatch,kind):
    old=fake_proc(tmp_path,monkeypatch,kind)
    with pytest.raises(m.InstallError):m.discover_old(old)


def test_verify_listener_never_accepts_another_server(tmp_path,monkeypatch):
    installer=m.Installer(tmp_path)
    monkeypatch.setattr(installer,'run',lambda *a,**k:b'555\n')
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:SimpleNamespace(stdout=b'pid=777,fd=1'))
    with pytest.raises(m.InstallError):installer.verify_listener(5059)


def test_activation_failure_restores_old_without_killing_portal(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'public_probe',lambda *a,**k:None)
    installer=m.Installer(tmp_path);(installer.root/'private').mkdir(parents=True)
    installer.old.mkdir();events=[];status={'port':True,'unit':5059,'failed':False}
    launch={'pid':1234,'start':'98765','argv':['.venv/bin/python','run.py'],'env':{'SYNTHETIC':'placeholder'}}
    monkeypatch.setattr(m,'discover_old',lambda old:launch.copy())
    monkeypatch.setattr(m.os,'pidfd_open',lambda pid:42)
    monkeypatch.setattr(m.os,'close',lambda fd:None)
    def terminate(fd,sig):events.append(('terminate',fd));status['port']=False
    monkeypatch.setattr(m.signal,'pidfd_send_signal',terminate)
    monkeypatch.setattr(m,'port_open',lambda p:status['port'] if p==5057 else False)
    def run(args,label,**kw):
        events.append(('run',tuple(args)))
        if args[-1]==m.UNIT and 'start' in args and status['unit']==5057:status['port']=True
        return b''
    monkeypatch.setattr(installer,'run',run)
    monkeypatch.setattr(installer,'write_unit',lambda r,p:status.update(unit=p))
    def health(port,origin,code=None):
        if port==5057 and not status['failed']:
            status['failed']=True;raise m.InstallError('synthetic-failure')
    monkeypatch.setattr(installer,'wait_health',health)
    monkeypatch.setattr(installer,'verify_listener',lambda port:None)
    def stop(*a,**kw):status['port']=False;return SimpleNamespace(returncode=0)
    monkeypatch.setattr(m.subprocess,'run',stop)
    def restore(*a,**kw):events.append(('restore',kw['cwd']));status['port']=True
    monkeypatch.setattr(m.subprocess,'Popen',restore)
    state={'port':5059,'old_pid':1234,'old_start':'98765','release':str(installer.root/'releases'/m.COMMIT),'origin':'https://demo.example'}
    with pytest.raises(m.InstallError,match='Rückkehr'):installer.activate(state)
    assert ('restore',installer.old) in events and status['port'] and status['unit']==5059
    assert [e for e in events if e[0]=='terminate']==[('terminate',42)]
    assert not any('nginx' in str(e) or '5000' in str(e) for e in events)


def test_changed_old_pid_aborts_before_any_stop(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'public_probe',lambda *a,**k:None)
    installer=m.Installer(tmp_path);calls=[]
    monkeypatch.setattr(m,'discover_old',lambda p:{'pid':77,'start':'new'})
    monkeypatch.setattr(installer,'run',lambda *a,**k:calls.append(a))
    with pytest.raises(m.InstallError):installer.activate({'port':5059,'old_pid':12,'old_start':'old','origin':'https://demo.example'})
    assert not calls


def test_full_staging_uses_synthetic_tests_before_config_and_is_idempotent(tmp_path,monkeypatch,capsys):
    installer=m.Installer(tmp_path);installer.old.mkdir()
    cfg=installer.old/'config.ini'
    cfg.write_text('[adler]\ndemo_code = synthetic-old-login-code\npublic_origin = https://demo.example\n')
    installer.unit=tmp_path/'fake-systemd.service'
    source=tmp_path/'source.zip';source.write_bytes(b'placeholder')
    launch={'pid':1234,'start':'98765','argv':['.venv/bin/python','run.py'],'env':{'SYNTHETIC':'private-placeholder'}}
    monkeypatch.setattr(m,'discover_old',lambda old:launch)
    monkeypatch.setattr(m,'port_open',lambda port:False)
    monkeypatch.setattr(m,'checked_payload',lambda data:{'run.py':b'# synthetic','requirements-dev.txt':b''})
    monkeypatch.setattr(m.shutil,'disk_usage',lambda path:SimpleNamespace(free=2**30))
    calls=[];checks=[]
    def run(args,label,timeout=180,cwd=None):
        calls.append(args)
        if 'pytest' in args:
            assert cwd==installer.root/'releases'/m.COMMIT
            assert not (cwd/'config.ini').exists(), 'real config must not be visible to tests'
        return b''
    monkeypatch.setattr(installer,'run',run)
    monkeypatch.setattr(installer,'write_unit',lambda release,port:installer.unit.write_text(m.unit_text(release,port,installer.root/'private/candidate.env')))
    monkeypatch.setattr(installer,'verify_listener',lambda port:None)
    monkeypatch.setattr(m,'health',lambda port,origin,demo_code=None:checks.append((port,demo_code)))
    before=cfg.read_bytes()
    state=installer.install(source)
    assert state['port']==5059 and cfg.read_bytes()==before
    assert len(list((installer.root/'backups').glob('*.tar.gz')))==1
    assert checks[0]==(5057,None)
    assert checks[-1][0]==5059 and checks[-1][1] not in (None,'synthetic-old-login-code')
    assert not any('kill' in str(c) or 'nginx' in str(c) or '5000' in str(c) for c in calls)
    count=len(calls);installer.install(source)
    assert len(calls)==count and len(list((installer.root/'backups').glob('*.tar.gz')))==1
    output=capsys.readouterr().out
    assert 'synthetic-old-login-code' not in output and checks[1][1] not in output


def test_https_origin_local_health_uses_synthetic_secure_cookie_only():
    import threading
    from adler import create_app
    from waitress import create_server
    app=create_app(overrides={'TESTING':True,'DEMO_CODE':'synthetic-local-health-code','PUBLIC_ORIGIN':'https://demo.example'})
    try:
        server=create_server(app,host='127.0.0.1',port=0,threads=2)
    except PermissionError:
        pytest.skip('sandbox does not permit local sockets')
    worker=threading.Thread(target=server.run,daemon=True);worker.start()
    try:
        m.health(server.effective_port,'https://demo.example','synthetic-local-health-code')
        assert not app.extensions['adler']['sessions']
    finally:
        server.close();worker.join(timeout=2)


def test_duplicate_zip_entry_is_rejected(monkeypatch):
    with pytest.warns(UserWarning,match='Duplicate name'):
        raw=archive(monkeypatch,('root/run.py',''))
    with pytest.raises(m.InstallError):m.checked_payload(raw)


def test_emergency_load_state_does_not_need_running_new_service(tmp_path,monkeypatch):
    installer=m.Installer(tmp_path);(installer.root/'private').mkdir(parents=True)
    release=installer.root/'releases'/m.COMMIT
    state={'commit':m.COMMIT,'release':str(release),'port':5057,'origin':'https://demo.example'}
    installer.unit=tmp_path/'unit.service'
    installer.unit.write_text(m.unit_text(release,5057,installer.root/'private/candidate.env'))
    m.private_write(installer.root/'private/state.json',json.dumps(state))
    monkeypatch.setattr(installer,'verify_listener',lambda p:pytest.fail('emergency load must not require a running new service'))
    assert installer.load_state()==state

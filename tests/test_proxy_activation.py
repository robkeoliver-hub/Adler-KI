"""Synthetic config files only; never runs system nginx/systemctl."""
import importlib.util
import json
import runpy
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('activation',ROOT/'scripts/activate_test_proxy.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
API=runpy.run_path(str(ROOT/'scripts/preview_test_proxy.py'))
SITE='''server {
 listen 443 ssl;
 server_name adlerzug.duckdns.org;
 location ^~ /demo/ki-adler/ { proxy_pass http://127.0.0.1:5057; }
 location / { proxy_pass http://127.0.0.1:5000; }
}
'''


@pytest.fixture
def controller(tmp_path,monkeypatch):
    state=tmp_path/'private';state.mkdir(mode=0o700)
    target=tmp_path/'club.conf';target.write_text(SITE)
    name='/etc/nginx/sites-enabled/club'
    files={m.MAIN:'events {} http { include /etc/nginx/sites-enabled/*; }',name:SITE}
    _,_,candidate=API['make_candidate']({name:SITE});candidate=candidate.encode();original=target.read_bytes()
    access=tmp_path/'ki-adler-portaltest/private';access.mkdir(parents=True,exist_ok=True)
    (access/'access.json').write_text(json.dumps({'paths':[m.PREFIX+'jugend/'+'A'*32,m.PREFIX+'jugend/'+'B'*32]}))
    c=m.Activation(tmp_path,state,API);calls=[]
    monkeypatch.setattr(c,'mount_ready',lambda:calls.append('mount'))
    monkeypatch.setattr(c,'candidate',lambda:(files,name,target,target.read_bytes(),candidate))
    monkeypatch.setattr(c,'syntax_candidate',lambda *args:calls.append('syntax'))
    monkeypatch.setattr(c,'run',lambda args:calls.append(tuple(args)) or '')
    monkeypatch.setattr(c,'probe',lambda url,**kwargs:calls.append(('probe',url)))
    # Only this synthetic temp target stands in for /etc/nginx during restore.
    real=type(Path())
    class SafeTestPath(real):
        def is_relative_to(self,other):
            if str(self)==str(target) and str(other)=='/etc/nginx':return True
            return super().is_relative_to(other)
    monkeypatch.setattr(m,'Path',SafeTestPath)
    return c,target,original,candidate,calls,files,name


def test_check_does_not_write_active_config_or_reload(controller):
    c,target,original,candidate,calls,*_=controller;c.check()
    assert target.read_bytes()==original
    assert 'syntax' in calls and not any(isinstance(x,tuple) and 'reload' in x for x in calls)
    assert json.loads((c.state/'proposal.json').read_text())['applied'] is False
    assert (c.state/'candidate.conf').stat().st_mode&0o777==0o600


def test_apply_requires_unchanged_checked_config(controller):
    c,target,original,candidate,calls,*_=controller;c.check();calls.clear()
    target.write_text(SITE+'# changed')
    with pytest.raises(m.ProxyError):c.apply()
    assert target.read_text()==SITE+'# changed'
    assert not (c.state/'original-before-apply.conf').exists()
    assert not any(isinstance(x,tuple) and 'reload' in x for x in calls)


def test_successful_apply_and_explicit_rollback(controller):
    c,target,original,candidate,calls,*_=controller;c.check()
    access=c.home/'ki-adler-portaltest/private';access.mkdir(parents=True,exist_ok=True)
    (access/'access.json').write_text(json.dumps({'paths':[m.PREFIX+'jugend/'+'A'*32,m.PREFIX+'jugend/'+'B'*32]}))
    c.apply()
    assert target.read_bytes()==candidate
    assert json.loads((c.state/'applied.json').read_text())['applied'] is True
    c.rollback()
    assert target.read_bytes()==original
    assert json.loads((c.state/'applied.json').read_text())['applied'] is False


@pytest.mark.parametrize('fail_at',['syntax_live','reload','https'])
def test_activation_failure_restores_original(controller,monkeypatch,fail_at):
    c,target,original,candidate,calls,*_=controller;c.check();failed=[False]
    def run(args):
        calls.append(tuple(args))
        if not failed[0] and ((fail_at=='syntax_live' and args==['nginx','-t']) or (fail_at=='reload' and args==['systemctl','reload','nginx'])):
            failed[0]=True;raise m.ProxyError('synthetic failure')
        return ''
    def probe(url,**kwargs):
        if fail_at=='https' and url=='https://'+m.HOST+m.PREFIX:raise OSError('synthetic private error')
    monkeypatch.setattr(c,'run',run);monkeypatch.setattr(c,'probe',probe)
    with pytest.raises(m.ProxyError,match='ursprüngliche Site'):c.apply()
    assert target.read_bytes()==original
    assert ('systemctl','reload','nginx') in calls
    assert json.loads((c.state/'applied.json').read_text())['applied'] is False


def test_rollback_refuses_foreign_changes(controller):
    c,target,original,candidate,calls,files,name=controller
    record=c.plan(files,name,target,original,candidate);record['applied']=True
    m.atomic(c.state/'original-before-apply.conf',original);target.write_text('foreign change')
    with pytest.raises(m.ProxyError):c.restore(record)
    assert target.read_text()=='foreign change'


def test_cloned_includes_preserve_non_target_configuration(tmp_path):
    names={m.MAIN:'events {} http { include /etc/nginx/sites-enabled/*; }',
           '/etc/nginx/sites-enabled/club':SITE,
           '/etc/nginx/sites-enabled/printer':'server { listen 80; location /webcam/ { proxy_pass http://127.0.0.1:9999; } }'}
    mapping={n:tmp_path/('c'+str(i)+'.conf') for i,n in enumerate(names)}
    output=m.clone_text(names[m.MAIN],names,mapping,API['tokens'])
    assert str(mapping['/etc/nginx/sites-enabled/club']) in output
    assert str(mapping['/etc/nginx/sites-enabled/printer']) in output
    assert m.clone_text(names['/etc/nginx/sites-enabled/printer'],names,mapping,API['tokens'])==names['/etc/nginx/sites-enabled/printer']


def test_include_globs_cannot_cross_directories():
    assert m.include_match('/etc/nginx/sites-enabled/a','/etc/nginx/sites-enabled/*')
    assert not m.include_match('/etc/nginx/sites-enabled/nested/a','/etc/nginx/sites-enabled/*')
    with pytest.raises(m.ProxyError):m.include_match('/etc/nginx/a','/etc/nginx/**')


@pytest.mark.parametrize('source',['include missing.conf;','ssl_certificate relative.pem;','ssl_certificate_key $dynamic;'])
def test_unknown_config_dependencies_refuse_clone(source):
    with pytest.raises(m.ProxyError):m.clone_text(source,{}, {},API['tokens'])


def test_real_clone_builder_only_invokes_nginx_test(tmp_path):
    c=m.Activation(tmp_path,tmp_path,API)
    site='/etc/nginx/sites-enabled/club'
    files={m.MAIN:'events {} http { include sites-enabled/*; }',site:SITE};runs=[]
    def fake_run(args):
        assert args[:3]==['nginx','-t','-c']
        main=Path(args[3]);assert main.exists()
        text=main.read_text();assert 'include "' in text and 'sites-enabled/*' not in text
        runs.append(args)
        return ''
    c.run=fake_run;c.syntax_candidate(files,site,(SITE+'\n# synthetic candidate').encode())
    assert len(runs)==1


def test_interrupted_apply_can_be_rolled_back(controller):
    c,target,original,candidate,calls,files,name=controller
    record=c.plan(files,name,target,original,candidate);record['pending']=True
    m.atomic(c.state/'original-before-apply.conf',original)
    m.atomic(c.state/'applied.json',json.dumps(record).encode())
    target.write_bytes(candidate)
    c.rollback()
    assert target.read_bytes()==original
    state=json.loads((c.state/'applied.json').read_text())
    assert not state['pending'] and not state['applied']


def test_relative_module_prefix_is_preserved():
    # No -p override: nginx resolves load_module against its unchanged compiled prefix.
    source='load_module modules/synthetic.so;'
    assert m.clone_text(source,{}, {},API['tokens'])==source


def test_missing_test_links_prevent_activation(controller):
    c,target,original,candidate,calls,*_=controller;c.check();calls.clear()
    (c.home/'ki-adler-portaltest/private/access.json').write_text('{}')
    with pytest.raises(m.ProxyError):c.apply()
    assert target.read_bytes()==original and not (c.state/'original-before-apply.conf').exists()

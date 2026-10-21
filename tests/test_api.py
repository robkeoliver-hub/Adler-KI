import time
import pytest
from adler import create_app
from adler.data import Principal, DemoData
from adler.providers import ProviderError

P='/demo/ki-adler'
ORIGIN='http://localhost'

@pytest.fixture
def app():
    return create_app(overrides={'TESTING':True,'DEMO_CODE':'synthetic-test-code-12345','PUBLIC_ORIGIN':ORIGIN})

@pytest.fixture
def client(app): return app.test_client()

def login(c):
    r=c.post(P+'/api/login',json={'code':'synthetic-test-code-12345'},headers={'Origin':ORIGIN})
    assert r.status_code==200
    return {'Origin':ORIGIN,'X-CSRF-Token':r.json['csrf']}

def test_shell_and_security_headers(client):
    r=client.get(P+'/');assert r.status_code==200
    assert "default-src 'self'" in r.headers['Content-Security-Policy']
    assert r.headers['Cache-Control']=='no-store'
    assert client.get('/').status_code==404
    assert client.get('/jugend/token').status_code==404

def test_no_public_data(client):
    for route in ['me','session']:
        assert client.get(P+'/api/'+route).status_code==401
    assert client.post(P+'/api/chat',json={'message':'hi'},headers={'Origin':ORIGIN}).status_code==401

def test_login_csrf_and_origin(client):
    assert client.post(P+'/api/login',json={'code':'wrong'},headers={'Origin':ORIGIN}).status_code==401
    assert client.post(P+'/api/login',json={'code':'synthetic-test-code-12345'}).status_code==403
    h=login(client)
    assert client.post(P+'/api/chat',json={'message':'hi'},headers={'Origin':ORIGIN}).status_code==403
    assert client.post(P+'/api/chat',json={'message':'hi'},headers={**h,'Origin':'https://evil.example'}).status_code==403
    assert client.post(P+'/api/chat',json={'message':'hi'},headers=h).status_code==200

def test_cookie(client):
    r=client.post(P+'/api/login',json={'code':'synthetic-test-code-12345'},headers={'Origin':ORIGIN})
    cookie=r.headers['Set-Cookie'];assert 'HttpOnly' in cookie and 'SameSite=Strict' in cookie
    assert 'Path=/demo/ki-adler/' in cookie

def test_forged_cookie(client):
    client.set_cookie('adler_demo','forged',path=P+'/')
    assert client.get(P+'/api/me').status_code==401

def test_identity_injection(client):
    h=login(client)
    for body in [{'message':'hi','user_id':2},{'message':'hi','role':'coach'},{'message':'hi','history':[]}]:
        assert client.post(P+'/api/chat',json=body,headers=h).status_code==400
    assert client.get(P+'/api/me?user_id=2').status_code==400
    assert client.get(P+'/api/me').json['synthetic'] is True

def test_deny_unknown_role_and_subject():
    for p in [Principal('other','youth'),Principal('synthetic-youth','coach'),Principal('synthetic-youth','admin')]:
        with pytest.raises(PermissionError): DemoData().snapshot(p)

def test_role_denied_via_api(app,client):
    h=login(client)
    state=next(iter(app.extensions['adler']['sessions'].values()))
    state['principal']=Principal('other','coach')
    assert client.get(P+'/api/me').status_code==403
    assert client.post(P+'/api/chat',json={'message':'Mein Training'},headers=h).status_code==403

def test_personal_tools_do_not_call_provider(app,client):
    h=login(client)
    def fail(_): raise AssertionError('provider called for personal tool')
    app.extensions['adler']['provider'].reply=fail
    for text in ['Wie habe ich geschossen?','Bin ich besser geworden?','Welches Abzeichen habe ich?','Wann ist das nächste Training?']:
        r=client.post(P+'/api/chat',json={'message':text},headers=h)
        assert r.status_code==200 and r.json['synthetic']

def test_validation(client):
    h=login(client)
    for value in ['', ' '*5, 'x'*601, 3, [],None]:
        assert client.post(P+'/api/chat',json={'message':value},headers=h).status_code==400
    assert client.post(P+'/api/chat',data='[]',content_type='application/json',headers=h).status_code==400
    assert client.post(P+'/api/chat',data='invalid',content_type='application/json',headers=h).status_code==400
    assert client.post(P+'/api/chat',data='hi',headers=h).status_code==415
    assert client.post(P+'/api/chat',json={'message':'x'*9000},headers=h).status_code==413

def test_chat_limit_and_login_limit(client):
    h=login(client)
    for _ in range(10): assert client.post(P+'/api/chat',json={'message':'hallo'},headers=h).status_code==200
    assert client.post(P+'/api/chat',json={'message':'hallo'},headers=h).status_code==429
    for _ in range(4):client.post(P+'/api/login',json={'code':'bad'},headers={'Origin':ORIGIN})
    assert client.post(P+'/api/login',json={'code':'bad'},headers={'Origin':ORIGIN}).status_code==429

def test_history_bounded(app,client):
    h=login(client)
    for _ in range(9):client.post(P+'/api/chat',json={'message':'Hallo'},headers=h)
    state=next(iter(app.extensions['adler']['sessions'].values()))
    assert len(state['history'])==8

def test_expiry(app,client):
    login(client)
    next(iter(app.extensions['adler']['sessions'].values()))['expires']=time.monotonic()-1
    assert client.get(P+'/api/me').status_code==401
    assert not app.extensions['adler']['sessions']

def test_logout_and_new_session(app,client):
    h=login(client)
    assert client.post(P+'/api/logout',json={},headers=h).status_code==200
    assert client.get(P+'/api/me').status_code==401
    assert not app.extensions['adler']['sessions']

def test_provider_error_no_details(app,client):
    h=login(client)
    def fail(_): raise ProviderError('secret-key-personal-prompt')
    app.extensions['adler']['provider'].reply=fail
    r=client.post(P+'/api/chat',json={'message':'hi'},headers=h)
    assert r.status_code==502
    assert 'secret' not in r.get_data(as_text=True)
    assert not next(iter(app.extensions['adler']['sessions'].values()))['busy']

def test_no_prompt_html_execution(client):
    h=login(client)
    r=client.post(P+'/api/chat',json={'message':'<img src=x onerror=alert(1)>'},headers=h)
    assert r.status_code==200 and r.content_type=='application/json'

def test_providers_fail_closed():
    common={'DEMO_CODE':'1234567890123456','PUBLIC_ORIGIN':ORIGIN,'PROVIDER':'compatible'}
    with pytest.raises(ValueError):create_app(overrides=common)
    with pytest.raises(ValueError):create_app(overrides={**common,'EXTERNAL_APPROVED':True,'ENDPOINT':'http://bad.test','MODEL':'test'})
    with pytest.raises(ValueError):create_app(overrides={'DEMO_CODE':'short'})

def test_secure_cookie_and_external_consent():
    a=create_app(overrides={'TESTING':True,'DEMO_CODE':'synthetic-test-code-12345','PUBLIC_ORIGIN':'https://demo.example','PROVIDER':'compatible','EXTERNAL_APPROVED':True,'ENDPOINT':'https://model.example/v1/chat/completions','MODEL':'test'})
    c=a.test_client(); r=c.post(P+'/api/login',json={'code':'synthetic-test-code-12345'},base_url='https://demo.example',headers={'Origin':'https://demo.example'})
    assert 'Secure;' in r.headers['Set-Cookie']
    headers={'Origin':'https://demo.example','X-CSRF-Token':r.json['csrf']}
    r=c.post(P+'/api/chat',json={'message':'hi'},base_url='https://demo.example',headers=headers)
    assert r.status_code==403

def test_foreign_host_rejected(client):
    assert client.get(P+'/',headers={'Host':'evil.example'}).status_code==400

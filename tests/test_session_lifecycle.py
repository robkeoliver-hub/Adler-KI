"""Revocation regressions, including a genuinely in-flight provider request."""
import threading
import time
from collections import OrderedDict

import pytest

from adler import create_app
from adler.data import Principal
from adler.sessions import discard_session, expire_sessions, is_current_session, cleanup_delay

P = '/demo/ki-adler'
ORIGIN = 'http://localhost'
CODE = 'synthetic-lifecycle-test-code'


def app_and_client():
    app = create_app(overrides={'TESTING': True, 'PUBLIC_ORIGIN': ORIGIN, 'DEMO_CODE': CODE})
    return app, app.test_client()


def login(client):
    response = client.post(P + '/api/login', json={'code': CODE}, headers={'Origin': ORIGIN})
    assert response.status_code == 200
    return {'Origin': ORIGIN, 'X-CSRF-Token': response.json['csrf']}


def state_at(deadline):
    return {'history': [{'role': 'user', 'content': 'synthetic-context'}],
            'expires': deadline, 'principal': Principal('synthetic-youth', 'youth')}


def test_logout_erases_existing_references():
    app, client = app_and_client()
    headers = login(client)
    assert client.post(P + '/api/chat', json={'message': 'Hallo'}, headers=headers).status_code == 200
    registry = app.extensions['adler']['sessions']
    state = next(iter(registry.values()))
    history = state['history']
    assert history
    assert client.post(P + '/api/logout', json={}, headers=headers).status_code == 200
    assert not registry and history == [] and state['history'] == []
    assert state['revoked'] is True


def test_relogin_erases_previous_context_and_rotates_cookie():
    app, client = app_and_client()
    headers = login(client)
    client.post(P + '/api/chat', json={'message': 'Hallo'}, headers=headers)
    registry = app.extensions['adler']['sessions']
    old = next(iter(registry.values()))
    cookie = client.get_cookie('adler_demo', path=P + '/').value
    login(client)
    assert old['history'] == [] and old['revoked']
    assert client.get_cookie('adler_demo', path=P + '/').value != cookie
    assert len(registry) == 1
    assert next(iter(registry.values()))['history'] == []


@pytest.mark.parametrize('action', ['logout', 'relogin', 'expiry', 'role', 'subject', 'shutdown'])
def test_inflight_reply_cannot_restore_revoked_context_or_be_returned(action):
    app, client = app_and_client()
    headers = login(client)
    client.post(P + '/api/chat', json={'message': 'Hallo'}, headers=headers)
    registry = app.extensions['adler']['sessions']
    state = next(iter(registry.values()))
    history_reference = state['history']
    entered, resume = threading.Event(), threading.Event()
    sentinel = 'SYNTHETIC-LATE-REPLY-NOT-TO-RETURN'
    result = {}

    def blocked_provider(messages):
        entered.set()
        assert resume.wait(3), 'test did not release provider'
        return sentinel

    app.extensions['adler']['provider'].reply = blocked_provider
    worker_client = app.test_client()
    worker_client.set_cookie('adler_demo', client.get_cookie('adler_demo', path=P + '/').value, path=P + '/')

    def request():
        try:
            result['response'] = worker_client.post(P + '/api/chat', json={'message': 'Erzähle etwas'}, headers=headers)
        except BaseException as exc:
            result['error'] = exc

    worker = threading.Thread(target=request)
    worker.start()
    try:
        assert entered.wait(3), 'provider never started'
        if action == 'logout':
            assert client.post(P + '/api/logout', json={}, headers=headers).status_code == 200
        elif action == 'relogin':
            login(client)
        elif action == 'expiry':
            state['expires'] = time.monotonic() - 1
            app.extensions['adler']['sweep']()
        elif action == 'role':
            state['principal'] = Principal('synthetic-youth', 'coach')
        elif action == 'subject':
            state['principal'] = Principal('another-synthetic-youth', 'youth')
        else:
            app.extensions['adler']['shutdown']()
    finally:
        resume.set()
        worker.join(timeout=3)
    assert not worker.is_alive()
    assert 'error' not in result, result.get('error')
    response = result['response']
    assert response.status_code == 401
    assert sentinel not in response.get_data(as_text=True)
    assert history_reference == [] and state['history'] == []
    assert all(sentinel not in str(item['history']) for item in registry.values())


def test_revoked_before_provider_does_not_send_any_context():
    app, client = app_and_client()
    headers = login(client)
    registry = app.extensions['adler']['sessions']

    def revoke_then_defer(principal, question):
        discard_session(registry, next(iter(registry)))
        return None

    def forbidden_provider(messages):
        pytest.fail('provider must not receive a request after preflight revocation')

    app.extensions['adler']['repository'].answer = revoke_then_defer
    app.extensions['adler']['provider'].reply = forbidden_provider
    response = client.post(P + '/api/chat', json={'message': 'Hallo'}, headers=headers)
    assert response.status_code == 401
    assert not registry


def test_sweep_expires_at_boundary_without_another_http_request():
    app, client = app_and_client()
    login(client)
    registry = app.extensions['adler']['sessions']
    state = next(iter(registry.values()))
    state['history'].append({'role': 'user', 'content': 'synthetic-context'})
    reference = state['history']
    state['expires'] = time.monotonic() - 1
    app.extensions['adler']['sweep']()
    assert not registry and reference == []


def test_expiry_boundaries_and_cleanup_deadline():
    state = state_at(900)
    registry = OrderedDict(sid=state)
    principal = state['principal']
    assert is_current_session(registry, 'sid', state, principal, 899)
    assert cleanup_delay(registry, 899) == 1
    expire_sessions(registry, 899.999)
    assert registry
    expire_sessions(registry, 900)
    assert not registry and state['history'] == []
    assert cleanup_delay(registry, 900) == 30
    assert not is_current_session(registry, 'sid', state, principal, 900)


def test_cookie_collision_or_replaced_entry_never_authorizes_old_state():
    old = state_at(900)
    new = state_at(900)
    registry = {'sid': new}
    assert not is_current_session(registry, 'sid', old, old['principal'], 1)
    assert registry['sid'] is new
    assert new['history']


@pytest.mark.parametrize('ttl', [0, -1, 901, True, '900', 900.5, float('nan')])
def test_context_lifetime_cannot_be_configured_above_privacy_limit(ttl):
    with pytest.raises(ValueError, match='SESSION_TTL'):
        create_app(overrides={'TESTING': True, 'DEMO_CODE': CODE, 'PUBLIC_ORIGIN': ORIGIN, 'SESSION_TTL': ttl})


def test_real_cleanup_worker_removes_idle_context_and_can_stop():
    # One bounded real-time check of the sleeping worker, no request triggers expiry.
    app = create_app(overrides={'DEMO_CODE': CODE, 'PUBLIC_ORIGIN': ORIGIN, 'SESSION_TTL': 1})
    client = app.test_client()
    try:
        login(client)
        state = next(iter(app.extensions['adler']['sessions'].values()))
        state['history'].append({'role': 'user', 'content': 'synthetic-worker-context'})
        deadline = time.monotonic() + 3
        while not state.get('revoked') and time.monotonic() < deadline:
            threading.Event().wait(0.02)
        assert state.get('revoked') and state['history'] == []
        assert not app.extensions['adler']['sessions']
    finally:
        app.extensions['adler']['shutdown']()

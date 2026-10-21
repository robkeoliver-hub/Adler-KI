
import pytest

from adler import create_app
from adler.config import ConfigurationError, load_settings
from test_api import P, ORIGIN

CODE = 'synthetic-config-test-code'


def settings(tmp_path, env=None, overrides=None):
    path = tmp_path / 'config.ini'
    path.write_text('[adler]\ndemo_code = ' + CODE + '\npublic_origin = http://localhost\n', encoding='utf-8')
    return load_settings(path, overrides=overrides, environ=env or {})


def test_legacy_ini_is_compatible_and_defaults_safe(tmp_path):
    value = settings(tmp_path)
    assert value['MODE'] == 'demo' and value['PROVIDER'] == 'mock'
    assert value['EXTERNAL_APPROVED'] is False
    assert value['BIND_HOST'] == '127.0.0.1' and value['PORT'] == 5057
    assert value['SESSION_TTL'] == 900


def test_env_overrides_ini_and_trusted_overrides_are_last(tmp_path):
    value = settings(tmp_path, {'ADLER_DEMO_CODE': 'synthetic-env-code-1234', 'ADLER_PORT': '5060', 'ADLER_SESSION_TTL': '120'}, {'PORT': 5061})
    assert value['DEMO_CODE'] == 'synthetic-env-code-1234'
    assert value['PORT'] == 5061 and value['SESSION_TTL'] == 120


def test_env_only_and_portable_config_location(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    value = load_settings(environ={'ADLER_DEMO_CODE': CODE})
    assert value['DEMO_CODE'] == CODE
    folder = tmp_path / 'Folder with spaces'
    folder.mkdir()
    config = folder / 'adler.ini'
    config.write_text('[adler]\ndemo_code = ' + CODE + '\n', encoding='utf-8')
    assert load_settings(environ={'ADLER_CONFIG_FILE': str(config)})['DEMO_CODE'] == CODE


def test_explicit_missing_or_broken_ini_does_not_fall_back(tmp_path):
    with pytest.raises(ConfigurationError):
        load_settings(tmp_path / 'missing.ini', environ={'ADLER_DEMO_CODE': CODE})
    bad = tmp_path / 'broken.ini'
    bad.write_text('[adler\napi_key = DO-NOT-EXPOSE-THIS-VALUE')
    with pytest.raises(ConfigurationError) as info:
        load_settings(bad, environ={})
    assert 'DO-NOT-EXPOSE' not in str(info.value)


@pytest.mark.parametrize('env', [
    {'ADLER_MODE': 'prod-typo'}, {'ADLER_MODE': ''},
    {'ADLER_PROVIDER': 'unknown'}, {'ADLER_DEMO_CODE': ''},
    {'ADLER_DEMO_CODE': 'HIER_EIGENEN_LANGEN_ZUFALLSCODE_EINTRAGEN'},
    {'ADLER_DEMO_CODE': 'ä' * 20}, {'ADLER_HOST': '0.0.0.0'},
    {'ADLER_PORT': '0'}, {'ADLER_PORT': '65536'}, {'ADLER_PORT': '1_234'},
    {'ADLER_PORT': '9' * 5000}, {'ADLER_SESSION_TTL': '901'},
    {'ADLER_SESSION_TTL': 'NaN'}, {'ADLER_EXTERNAL_APPROVED': 'yes'},
    {'ADLER_PUBLIC_ORIGIN': 'http://demo.example'},
    {'ADLER_PUBLIC_ORIGIN': 'https://name:secret@demo.example'},
    {'ADLER_PUBLIC_ORIGIN': 'https://demo.example/path'},
    {'ADLER_PUBLIC_ORIGIN': 'https://demo.example:99999'},
])
def test_bad_settings_fail_closed_without_echoing_values(tmp_path, env):
    with pytest.raises(ConfigurationError) as info:
        settings(tmp_path, env)
    assert 'secret' not in str(info.value) and 'ä' not in str(info.value)


@pytest.mark.parametrize('provider', ['mock', 'compatible'])
def test_production_never_constructs_demo_or_provider(monkeypatch, provider):
    def forbidden(*args, **kwargs):
        pytest.fail('production must fail before DemoData or providers are constructed')
    monkeypatch.setattr('adler.DemoData', forbidden)
    monkeypatch.setattr('adler.MockProvider', forbidden)
    monkeypatch.setattr('adler.CompatibleProvider', forbidden)
    monkeypatch.setenv('ADLER_MODE', 'production')
    monkeypatch.setenv('ADLER_PROVIDER', provider)
    monkeypatch.setenv('ADLER_ENDPOINT', 'https://model.example/v1/chat/completions')
    monkeypatch.setenv('ADLER_MODEL', 'synthetic-model')
    monkeypatch.setenv('ADLER_EXTERNAL_APPROVED', 'true')
    with pytest.raises(ConfigurationError, match='Produktivstart gesperrt'):
        create_app(overrides={'TESTING': True, 'DEMO_CODE': CODE})


def test_provider_approval_does_not_follow_from_key(tmp_path):
    env = {'ADLER_PROVIDER': 'compatible', 'ADLER_ENDPOINT': 'https://model.example/v1/chat/completions', 'ADLER_MODEL': 'synthetic-model', 'ADLER_API_KEY': 'synthetic-placeholder'}
    with pytest.raises(ConfigurationError):
        settings(tmp_path, env)
    value = settings(tmp_path, {**env, 'ADLER_EXTERNAL_APPROVED': 'true'})
    assert value['PROVIDER'] == 'compatible' and value['EXTERNAL_APPROVED'] is True


def test_empty_env_key_removes_ini_key_instead_of_falling_back(tmp_path):
    config = tmp_path / 'key.ini'
    config.write_text('[adler]\ndemo_code = ' + CODE + '\napi_key = synthetic-ini-placeholder\n')
    value = load_settings(config, environ={'ADLER_API_KEY': ''})
    assert value['API_KEY'] == ''


def test_ini_percent_in_key_not_interpolated(tmp_path):
    config = tmp_path / 'percent.ini'
    config.write_text('[adler]\ndemo_code = ' + CODE + '\napi_key = synthetic%placeholder\n')
    assert load_settings(config, environ={})['API_KEY'] == 'synthetic%placeholder'


def test_run_entrypoint_uses_validated_host_port(monkeypatch):
    import run
    captured = {}
    class App:
        config = {'BIND_HOST': '127.0.0.1', 'PORT': 5062}
    monkeypatch.setattr(run, 'create_app', lambda: App())
    monkeypatch.setattr(run, 'serve', lambda app, **kwargs: captured.update(kwargs))
    run.main()
    assert captured['host'] == '127.0.0.1' and captured['port'] == 5062
    assert captured['clear_untrusted_proxy_headers'] is True


def test_nonascii_login_and_csrf_rejected_without_server_error():
    app = create_app(overrides={'TESTING': True, 'DEMO_CODE': CODE, 'PUBLIC_ORIGIN': ORIGIN})
    c = app.test_client()
    assert c.post(P + '/api/login', json={'code': 'ä'}, headers={'Origin': ORIGIN}).status_code == 401
    assert c.post(P + '/api/login', json={'code': CODE}, headers={'Origin': ORIGIN}).status_code == 200
    assert c.post(P + '/api/chat', json={'message': 'Hallo'}, headers={'Origin': ORIGIN, 'X-CSRF-Token': 'ä'}).status_code == 403

"""Validated server configuration. No logging, secrets in errors or portal imports."""
import configparser
import os
import re
from pathlib import Path
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    pass


ENV_FIELDS = {
    'ADLER_MODE': 'MODE', 'ADLER_DEMO_CODE': 'DEMO_CODE',
    'ADLER_PUBLIC_ORIGIN': 'PUBLIC_ORIGIN', 'ADLER_PROVIDER': 'PROVIDER',
    'ADLER_ENDPOINT': 'ENDPOINT', 'ADLER_MODEL': 'MODEL', 'ADLER_API_KEY': 'API_KEY',
    'ADLER_EXTERNAL_APPROVED': 'EXTERNAL_APPROVED', 'ADLER_HOST': 'BIND_HOST',
    'ADLER_PORT': 'PORT', 'ADLER_SESSION_TTL': 'SESSION_TTL',
}
INI_FIELDS = {name.lower(): name for name in ENV_FIELDS.values()}
INI_FIELDS['host'] = 'BIND_HOST'


def _integer(value, name, minimum, maximum):
    if isinstance(value, bool):
        raise ConfigurationError(name + ' hat keinen gültigen Ganzzahlwert')
    if isinstance(value, str):
        if not re.fullmatch(r'[0-9]{1,5}', value):
            raise ConfigurationError(name + ' hat keinen gültigen Ganzzahlwert')
        value = int(value)
    if not isinstance(value, int) or not minimum <= value <= maximum:
        raise ConfigurationError(name + ' liegt außerhalb des erlaubten Bereichs')
    return value


def _boolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    raise ConfigurationError('EXTERNAL_APPROVED muss true oder false sein')


def _url(value, name):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ConfigurationError(name + ' ist ungültig')
    try:
        parsed = urlsplit(value)
        port = parsed.port  # Validate malformed/out-of-range ports without exposing input.
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError()
        if parsed.fragment or (port is not None and port < 1):
            raise ValueError()
    except ValueError:
        raise ConfigurationError(name + ' ist ungültig') from None
    return parsed


def load_settings(config_path=None, overrides=None, environ=None):
    """Defaults < optional legacy INI < ADLER_* env < trusted factory overrides.

    Production is deliberately unavailable until the real portal adapters exist.
    This prevents a synthetically populated app from starting as production.
    """
    env = os.environ if environ is None else environ
    values = dict(MODE='demo', MAX_CONTENT_LENGTH=8192, DEMO_CODE='',
                  PUBLIC_ORIGIN='http://127.0.0.1:5057', PROVIDER='mock',
                  ENDPOINT='', MODEL='', API_KEY='', EXTERNAL_APPROVED=False,
                  SESSION_TTL=900, CHAT_LIMIT=10, BIND_HOST='127.0.0.1', PORT=5057)
    explicit_path = config_path if config_path is not None else env.get('ADLER_CONFIG_FILE')
    path = Path(explicit_path).expanduser() if explicit_path is not None else Path(__file__).resolve().parent.parent / 'config.ini'
    cfg = configparser.ConfigParser(interpolation=None)
    try:
        if path.exists():
            with path.open(encoding='utf-8') as file:
                cfg.read_file(file)
        elif explicit_path is not None:
            raise ConfigurationError('Explizite Konfigurationsdatei fehlt')
        if cfg.has_section('adler'):
            for key, value in cfg['adler'].items():
                if key in INI_FIELDS:
                    values[INI_FIELDS[key]] = value
    except (OSError, UnicodeError, configparser.Error):
        raise ConfigurationError('Konfigurationsdatei kann nicht sicher gelesen werden') from None
    for key, field in ENV_FIELDS.items():
        if key in env:
            values[field] = env[key]  # An explicit empty value never falls back to an INI secret.
    if overrides:
        if 'SESSION_TTL' in overrides and (isinstance(overrides['SESSION_TTL'], bool) or not isinstance(overrides['SESSION_TTL'], int)):
            raise ConfigurationError('SESSION_TTL benötigt in Factory-Overrides einen Integer')
        values.update(overrides)

    if values['MODE'] not in ('demo', 'production'):
        raise ConfigurationError('MODE muss demo oder production sein')
    if values['MODE'] == 'production':
        raise ConfigurationError('Produktivstart gesperrt: geprüfte Portal-Auth- und Datenadapter fehlen; Demo-Fallback verboten')
    code = values['DEMO_CODE']
    if (not isinstance(code, str) or len(code) < 16
            or code == 'HIER_EIGENEN_LANGEN_ZUFALLSCODE_EINTRAGEN'):
        raise ConfigurationError('DEMO_CODE benötigt einen eigenen Zugangscode mit mindestens 16 Zeichen')
    try:
        code.encode('ascii')
    except UnicodeError:
        raise ConfigurationError('DEMO_CODE muss aus ASCII-Zeichen bestehen') from None
    values['SESSION_TTL'] = _integer(values['SESSION_TTL'], 'SESSION_TTL', 1, 900)
    values['PORT'] = _integer(values['PORT'], 'PORT', 1, 65535)
    values['EXTERNAL_APPROVED'] = _boolean(values['EXTERNAL_APPROVED'])
    if values['BIND_HOST'] not in ('127.0.0.1', 'localhost', '::1'):
        raise ConfigurationError('BIND_HOST muss Loopback sein')
    origin = _url(values['PUBLIC_ORIGIN'], 'PUBLIC_ORIGIN')
    if origin.scheme not in ('http', 'https') or origin.path or origin.query:
        raise ConfigurationError('PUBLIC_ORIGIN benötigt eine HTTP(S)-Origin ohne Pfad')
    if origin.scheme != 'https' and origin.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ConfigurationError('PUBLIC_ORIGIN benötigt außerhalb von Loopback HTTPS')
    if values['PROVIDER'] not in ('mock', 'compatible'):
        raise ConfigurationError('PROVIDER ist unbekannt')
    if values['PROVIDER'] == 'compatible':
        endpoint = _url(values['ENDPOINT'], 'ENDPOINT')
        if (not values['EXTERNAL_APPROVED'] or endpoint.scheme != 'https'
                or not isinstance(values['MODEL'], str) or not values['MODEL'].strip()):
            raise ConfigurationError('Provider benötigt Freigabe, HTTPS und Modell')
    return values

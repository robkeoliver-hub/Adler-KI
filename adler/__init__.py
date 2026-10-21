import atexit
import configparser
import hashlib
import secrets
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path
from urllib.parse import urlsplit
from flask import Flask, request, jsonify, render_template, g, abort
from .providers import MockProvider, CompatibleProvider, ProviderError
from .data import DemoData, Principal

PREFIX = '/demo/ki-adler'


def create_app(config_path=None, overrides=None):
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(config_path or Path(__file__).resolve().parent.parent / 'config.ini')
    section = cfg['adler'] if cfg.has_section('adler') else {}
    app = Flask(__name__, static_url_path=PREFIX + '/static')
    app.config.update(MAX_CONTENT_LENGTH=8192, DEMO_CODE=section.get('demo_code', ''),
        PUBLIC_ORIGIN=section.get('public_origin', 'http://127.0.0.1:5057'),
        PROVIDER=section.get('provider', 'mock'), ENDPOINT=section.get('endpoint', ''),
        MODEL=section.get('model', ''), API_KEY=section.get('api_key', ''),
        EXTERNAL_APPROVED=section.get('external_approved', 'false').lower() == 'true',
        SESSION_TTL=900, CHAT_LIMIT=10)
    if overrides: app.config.update(overrides)
    if len(app.config['DEMO_CODE']) < 16: raise ValueError('demo_code: mindestens 16 Zeichen')
    origin = app.config['PUBLIC_ORIGIN']
    parsed = urlsplit(origin)
    if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('public_origin muss eine Origin ohne Pfad sein')
    if parsed.scheme != 'https' and parsed.hostname not in ('127.0.0.1', 'localhost'):
        raise ValueError('Nicht-lokaler Zugriff erfordert HTTPS')
    if app.config['PROVIDER'] == 'mock': provider = MockProvider()
    elif app.config['PROVIDER'] == 'compatible':
        endpoint = urlsplit(app.config['ENDPOINT'])
        if not app.config['EXTERNAL_APPROVED'] or endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.fragment or not app.config['MODEL']:
            raise ValueError('Provider benötigt explizite Freigabe, HTTPS-Endpunkt und Modell')
        provider = CompatibleProvider(app.config['ENDPOINT'], app.config['MODEL'], app.config['API_KEY'])
    else: raise ValueError('Unbekannter Provider')
    store, buckets = OrderedDict(), OrderedDict()
    lock, upstream = threading.RLock(), threading.BoundedSemaphore(2)
    repository = DemoData()
    app.extensions['adler'] = {'sessions': store, 'provider': provider, 'repository': repository}
    # One sleeping daemon per app, no polling of provider or database.
    stop_cleanup = threading.Event()
    def cleanup():
        while not stop_cleanup.wait(30):
            now = time.monotonic()
            with lock:
                for key in list(store):
                    if store[key]['expires'] <= now: del store[key]
                for key in list(buckets):
                    if buckets[key]['seen'] < now - 600: del buckets[key]
    if not app.config.get('TESTING'):
        threading.Thread(target=cleanup, name='adler-session-expiry', daemon=True).start()
        atexit.register(stop_cleanup.set)
    cookie = '__Secure-adler_demo' if parsed.scheme == 'https' else 'adler_demo'
    secure = parsed.scheme == 'https'

    def limited(key, maximum, window=60):
        now = time.monotonic()
        with lock:
            while buckets and next(iter(buckets.values()))['seen'] < now - 600: buckets.popitem(last=False)
            item = buckets.setdefault(key, {'seen': now, 'times': deque()})
            buckets.move_to_end(key); item['seen'] = now
            while item['times'] and item['times'][0] < now-window: item['times'].popleft()
            if len(item['times']) >= maximum: return True
            item['times'].append(now)
            while len(buckets) > 1024: buckets.popitem(last=False)
            return False

    def payload(allowed):
        if not request.is_json: abort(415)
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) - set(allowed): abort(400)
        return data

    @app.before_request
    def guard():
        g.started = time.perf_counter()
        if request.host != parsed.netloc: abort(400)
        if request.method == 'POST' and request.headers.get('Origin') != origin: abort(403)
        if request.path.startswith(PREFIX + '/api/'):
            now = time.monotonic()
            with lock:
                for key in list(store):
                    if store[key]['expires'] <= now: del store[key]
                token = request.cookies.get(cookie, '')
                g.sid = hashlib.sha256(token.encode()).hexdigest()
                g.state = store.get(g.sid)
            # Login brute-force/global ceiling cannot be bypassed by fresh cookies.
            if request.path.endswith('/login'):
                if limited('login:' + (request.remote_addr or '?'), 5) or limited('login-global', 60): abort(429)
            else:
                if g.state is None: abort(401)
                if request.method == 'POST' and not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), g.state['csrf']): abort(403)
                if limited('api:' + g.sid, 40): abort(429)

    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
            'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
            'Permissions-Policy': 'microphone=(self), camera=(), geolocation=()',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"})
        if hasattr(g, 'started'): response.headers['Server-Timing'] = f'app;dur={(time.perf_counter()-g.started)*1000:.2f}'
        return response

    for status in [400, 401, 403, 404, 405, 413, 415, 429, 500, 502, 503]:
        def error(e, code=status):
            response = jsonify(error={401:'Bitte Demo-Zugang öffnen.',403:'Zugriff abgelehnt. Seite neu laden.',429:'Bitte kurz warten; Anfragelimit erreicht.',502:'KI-Dienst nicht erreichbar. Bitte später versuchen.',503:'KI-Adler ist gerade beschäftigt.'}.get(code,'Die Anfrage konnte nicht verarbeitet werden.'))
            response.status_code = code
            if code == 429: response.headers['Retry-After'] = '60'
            return response
        app.register_error_handler(status, error)

    @app.get(PREFIX + '/')
    def index(): return render_template('index.html')

    @app.post(PREFIX + '/api/login')
    def login():
        data = payload(['code'])
        if not isinstance(data.get('code'), str) or not secrets.compare_digest(data['code'], app.config['DEMO_CODE']): abort(401)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with lock:
            old = request.cookies.get(cookie, '')
            store.pop(hashlib.sha256(old.encode()).hexdigest(), None)
            if len(store) >= 128: abort(503)
            store[hashlib.sha256(token.encode()).hexdigest()] = dict(csrf=csrf, expires=time.monotonic()+app.config['SESSION_TTL'],
                principal=Principal('synthetic-youth','youth'), history=[], busy=False)
        response = jsonify(csrf=csrf, mode=app.config['PROVIDER'], ttl=app.config['SESSION_TTL'])
        response.set_cookie(cookie, token, secure=secure, httponly=True, samesite='Strict', path=PREFIX+'/', max_age=app.config['SESSION_TTL'])
        return response

    @app.get(PREFIX + '/api/session')
    def session_info(): return jsonify(csrf=g.state['csrf'], mode=app.config['PROVIDER'], ttl=max(0,int(g.state['expires']-time.monotonic())))

    @app.get(PREFIX + '/api/me')
    def me():
        if request.args: abort(400)
        try: return jsonify(repository.snapshot(g.state['principal']))
        except PermissionError: abort(403)

    @app.post(PREFIX + '/api/logout')
    def logout():
        payload([])
        with lock: store.pop(g.sid, None)
        response = jsonify(ok=True)
        response.delete_cookie(cookie, path=PREFIX+'/', secure=secure, httponly=True, samesite='Strict')
        return response

    @app.post(PREFIX + '/api/chat')
    def chat():
        data = payload(['message', 'external_consent'])
        if app.config['PROVIDER'] == 'compatible' and data.get('external_consent') is not True: abort(403)
        message = data.get('message')
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 600: abort(400)
        message = message.strip()
        if limited('chat:'+g.sid, app.config['CHAT_LIMIT']) or limited('chat-global', 30): abort(429)
        with lock:
            if g.state['busy']: abort(503)
            g.state['busy'] = True
            history = list(g.state['history'])
        try:
            try: answer = repository.answer(g.state['principal'], message)
            except PermissionError: abort(403)
            if answer is None:
                # Browser has no approval for personal content; provider mode only for synthetic tests.
                if not upstream.acquire(blocking=False): abort(503)
                try: answer = provider.reply(history + [{'role':'user', 'content':message}])
                except ProviderError: abort(502)
                finally: upstream.release()
            with lock:
                g.state['history'] = (history + [{'role':'user','content':message}, {'role':'assistant','content':answer}])[-8:]
            return jsonify(reply=answer, mode=app.config['PROVIDER'], synthetic=True, elapsed_ms=round((time.perf_counter()-g.started)*1000,2))
        finally:
            with lock: g.state['busy'] = False

    return app

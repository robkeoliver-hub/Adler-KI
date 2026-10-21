"""Opt-in extension for the existing Flask portal. No app import or DB writes."""
import hashlib
import hmac
import json
import math
import secrets
import threading
import time
from collections import OrderedDict
from datetime import date
from urllib.parse import urlsplit

from flask import Blueprint, abort, g, jsonify, render_template, request, session
from markupsafe import Markup


def init_portal_adler(app, *, youth_model, training_model, event_model, clock=time.monotonic):
    """Explicit host wiring; disabled by default, no fallback to demo data."""
    if app.config.get('ADLER_PORTAL_ENABLED') is not True:
        app.jinja_env.globals['ki_adler_panel'] = lambda: Markup('')
        return
    origin = app.config.get('ADLER_PORTAL_ORIGIN', '')
    parts = urlsplit(origin)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.path or parts.query or parts.fragment):
        raise ValueError('ADLER_PORTAL_ORIGIN muss eine genaue HTTPS-Origin ohne Pfad sein')
    secret = app.config.get('SECRET_KEY', '')
    if (not isinstance(secret, str) or len(secret) < 32 or 'REDACTED' in secret
            or not app.config.get('SESSION_COOKIE_SECURE')
            or not app.config.get('SESSION_COOKIE_HTTPONLY', True)
            or app.config.get('SESSION_COOKIE_SAMESITE') not in ('Lax', 'Strict')
            or app.config.get('ADLER_PORTAL_TOKEN_REVIEWED') is not True):
        raise ValueError('Portal-Integration erfordert geprüfte Tokenverwaltung und sichere Sessionkonfiguration')
    bp = Blueprint('portal_adler', __name__, url_prefix='/ki-adler',
                   template_folder='templates', static_folder='static')
    records, rates = OrderedDict(), OrderedDict()
    lock = threading.RLock()
    ttl = 900

    def digest(value):
        return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()

    def purge():
        now = clock()
        for key in list(records):
            if records[key]['until'] <= now:
                records.pop(key, None)
        for key in list(rates):
            if rates[key][0] + 60 <= now:
                rates.pop(key, None)

    def rate_limit():
        key = digest(request.remote_addr or 'unknown')
        with lock:
            purge()
            start, count = rates.get(key, (clock(), 0))
            if count >= 30 or (key not in rates and len(rates) >= 512):
                abort(429)
            rates[key] = (start, count + 1)

    def body():
        if request.mimetype != 'application/json':
            abort(415)
        raw = request.stream.read(2049)
        if len(raw) > 2048:
            abort(413)
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            abort(400)
        if not isinstance(value, dict):
            abort(400)
        return value

    def authorize_post():
        rate_limit()
        if request.headers.get('Origin') != origin:
            abort(403)
        expected = session.get('adler_portal_csrf')
        supplied = request.headers.get('X-CSRF-Token', '')
        if not isinstance(expected, str) or not hmac.compare_digest(expected.encode(), supplied.encode()):
            abort(403)

    def current():
        with lock:
            purge()
            sid = session.get('adler_portal_sid')
            state = records.get(sid)
            # Existing shared staff login never grants extra authority here.
            if not state or session.get('betreuer'):
                records.pop(sid, None)
                abort(401)
            if not hmac.compare_digest(sid.encode(), request.headers.get('X-Adler-Binding', '').encode()):
                abort(401)
            member = youth_model.query.filter_by(id=state['member'], aktiv=True).first()
            if not member or not hmac.compare_digest(digest(member.qr_token), state['fingerprint']):
                records.pop(sid, None)
                abort(401)
            return member

    @bp.after_request
    def private_response(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @bp.errorhandler(Exception)
    def safe_error(error):
        from werkzeug.exceptions import HTTPException
        status = error.code if isinstance(error, HTTPException) else 503
        # No exception values, tokens, bodies or personal content in logs/responses.
        return jsonify(error='Anfrage nicht verfügbar', status=status), status

    @bp.post('/session')
    def bind():
        authorize_post()
        value = body()
        if set(value) != {'token'} or not isinstance(value['token'], str) or not 24 <= len(value['token']) <= 128:
            abort(400)
        with lock:
            records.pop(session.pop('adler_portal_sid', None), None)
            if session.get('betreuer'):
                abort(403)
            member = youth_model.query.filter_by(qr_token=value['token'], aktiv=True).first()
            if not member:
                abort(401)
            purge()
            if len(records) >= 256:
                abort(503)
            sid = secrets.token_urlsafe(32)
            records[sid] = {'member': member.id, 'fingerprint': digest(member.qr_token), 'until': clock() + ttl}
            session['adler_portal_sid'] = sid
        return jsonify(binding=sid, expires_in=ttl, tools=['last_training', 'next_event'])

    @bp.post('/tool')
    def tool():
        authorize_post()
        value = body()
        if set(value) != {'tool'} or value['tool'] not in ('last_training', 'next_event'):
            abort(400)
        with lock:
            member = current()
            if value['tool'] == 'last_training':
                row = training_model.query.filter_by(jugendlicher_id=member.id).order_by(
                    training_model.datum.desc(), training_model.id.desc()).first()
                if row is None:
                    return jsonify(answer='Für dich ist noch kein Training gespeichert.', source='portal', data=None)
                score = float(row.ringzahl)
                if not math.isfinite(score):
                    abort(503)
                data = dict(date=row.datum, discipline=row.disziplin, score=score, shots=row.schuss_anzahl)
                answer = (f'Dein letztes gespeichertes Training war am {row.datum}: '
                          f'{score:g} Ringe bei {row.schuss_anzahl} Schuss ({row.disziplin}).')
            else:
                row = event_model.query.filter_by(zielgruppe='Jugend').filter(
                    event_model.datum >= date.today().isoformat()).order_by(
                    event_model.datum, event_model.uhrzeit, event_model.id).first()
                if row is None:
                    return jsonify(answer='Im Vereinskalender steht kein bevorstehender Jugendtermin.', source='portal', data=None)
                data = dict(date=row.datum, time=row.uhrzeit, title=row.titel, place=row.ort)
                answer = f'Der nächste Jugendtermin ist {row.titel} am {row.datum} um {row.uhrzeit}.'
            return jsonify(answer=answer, source='portal', data=data)

    @bp.post('/close')
    def close():
        authorize_post()
        with lock:
            sid = session.get('adler_portal_sid')
            if isinstance(sid, str) and hmac.compare_digest(sid.encode(), request.headers.get('X-Adler-Binding', '').encode()):
                records.pop(sid, None)
                session.pop('adler_portal_sid', None)
        return jsonify(closed=True)

    def panel():
        token = (request.view_args or {}).get('token')
        if (not request.endpoint or not request.endpoint.startswith('jugend_')
                or not isinstance(token, str) or len(token) < 24 or session.get('betreuer')):
            return Markup('')
        if not session.get('adler_portal_csrf'):
            session['adler_portal_csrf'] = secrets.token_urlsafe(32)
        g.adler_panel_rendered = True
        # Token is already in the existing route; never duplicate it in HTML/URLs.
        return Markup(render_template('portal_adler/panel.html', csrf=session['adler_portal_csrf']))

    @app.after_request
    def panel_headers(response):
        if getattr(g, 'adler_panel_rendered', False):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    app.register_blueprint(bp)
    app.jinja_env.globals['ki_adler_panel'] = panel
    # Lazy purge on every API request, no background process or chat persistence.
    # Absolute expiry disallows access after 15 min; bounded stale records are
    # reclaimed on the next request (maximum 256 principal records, no messages).

"""Opt-in extension for the existing Flask portal. No app import or DB writes."""
import base64
from pathlib import Path
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

from flask import Blueprint, abort, g, jsonify, render_template, request, session, Response, url_for
from markupsafe import Markup
from .dialogue import configured_provider, intent, local_greeting, Unavailable


def init_portal_adler(app, *, youth_model, training_model, event_model, clock=time.monotonic,
                      adult_model=None, adult_training_model=None, badge_reader=None, dialogue_provider=None):
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
    inference_slots = threading.BoundedSemaphore(2)
    janitor = [None, None]
    ttl = 900
    provider = dialogue_provider or configured_provider(app.config)
    models = {"youth": youth_model}
    if adult_model is not None:
        models["adult"] = adult_model

    def profile(member):
        # First name is displayed locally; full birth date never leaves the server.
        name = str(getattr(member, "vorname", "") or "")[:50]
        return {"display_name": name}

    def resolve(token):
        matches = [(kind, model.query.filter_by(qr_token=token, aktiv=True).first()) for kind, model in models.items()]
        matches = [(kind, member) for kind, member in matches if member is not None]
        if len(matches) != 1:abort(401)
        return matches[0]

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

    def cleanup_contexts():
        # One daemon timer for all conversations, no persistent process or per-user worker.
        with lock:
            janitor[:] = [None, None]
            purge()
            schedule_cleanup()

    def schedule_cleanup():
        deadlines = [s['until'] for s in records.values() if s.get('history')]
        if not deadlines:return
        deadline = min(deadlines)
        if janitor[0] is not None:
            if janitor[1] <= deadline:return
            janitor[0].cancel()
        timer = threading.Timer(max(.05, deadline-clock()), cleanup_contexts)
        timer.daemon = True
        janitor[:] = [timer, deadline]
        timer.start()

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

    def authorize_post(*, limit=True):
        if limit:rate_limit()
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
            member = models[state['kind']].query.filter_by(id=state['member'], aktiv=True).first()
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
            kind, member = resolve(value['token'])
            if not member:
                abort(401)
            purge()
            if len(records) >= 256:
                abort(503)
            sid = secrets.token_urlsafe(32)
            records[sid] = {'kind':kind, 'history':[], 'busy':False, 'member': member.id, 'fingerprint': digest(member.qr_token), 'until': clock() + ttl}
            session['adler_portal_sid'] = sid
        return jsonify(binding=sid, expires_in=ttl, profile=profile(member), dialogue_available=provider is not None,
                       tools=['last_training', 'next_event', 'progress', 'badges'])

    def read_tool(member, name):
        state = records[session['adler_portal_sid']]
        kind = state['kind']
        model = training_model if kind == 'youth' else adult_training_model
        if name in ('last_training', 'progress'):
            if model is None:
                return dict(answer='Deine Ergebnisansicht ist noch nicht angebunden. Nutze bitte das bestehende Portalmenü.', source='portal', data=None)
            fk = 'jugendlicher_id' if kind == 'youth' else 'erwachsener_id'
            query = model.query.filter_by(**{fk:member.id}).order_by(model.datum.desc(), model.id.desc())
            row = query.first()
            if row is None:
                return dict(answer='Für dich ist noch kein Training gespeichert.', source='portal', data=None)
            score = float(row.ringzahl)
            if not math.isfinite(score):abort(503)
            data = dict(date=row.datum, discipline=row.disziplin, score=score, shots=row.schuss_anzahl)
            answer = (f'Dein letztes gespeichertes Training war am {row.datum}: '
                      f'{score:g} Ringe bei {row.schuss_anzahl} Schuss ({row.disziplin}).')
            if name == 'progress':
                # Compare only same discipline, shot count AND scoring system, distinct days.
                previous = query.filter(model.datum < row.datum, model.disziplin == row.disziplin,
                                        model.schuss_anzahl == row.schuss_anzahl)
                if hasattr(model, 'wertung') and row.wertung:
                    previous = previous.filter(model.wertung == row.wertung)
                else:
                    return dict(answer=answer + ' Die Wertungsart ist nicht angebunden; deshalb vergleiche ich die Ergebnisse noch nicht.', source='portal', data=data)
                old = previous.first()
                if old is None:
                    answer += ' Ein früheres vergleichbares Training ist noch nicht gespeichert.'
                else:
                    old_score = float(old.ringzahl)
                    if not math.isfinite(old_score):abort(503)
                    diff = score-old_score
                    data['previous'] = dict(date=old.datum, score=old_score)
                    answer += f' Gegenüber dem {old.datum} sind das {abs(diff):g} Ringe ' + ('mehr.' if diff > 0 else 'weniger.' if diff < 0 else 'Unterschied.')
                    answer += ' Jedes Training zählt – Ergebnisse dürfen auch schwanken.'
        elif name == 'badges':
            if kind != 'youth' or badge_reader is None:
                return dict(answer='Deine Abzeichen findest du im bestehenden Abzeichenmenü. Die sichere Abzeichenverbindung ist hier noch nicht aktiviert.', source='portal', data=None)
            # Trusted host callback, never chosen or generated by the model/client.
            statuses = badge_reader(member)
            achieved = [str(item['abzeichen'].name)[:160] for item in statuses if item.get('erreicht')][:30]
            data = {'achieved':achieved}
            answer = 'Laut deinem Portal hast du erreicht: ' + ', '.join(achieved) + '.' if achieved else 'Für dich ist noch kein erreichtes Abzeichen im Portal vermerkt. Im Abzeichenmenü siehst du die Voraussetzungen.'
        else:
            target = 'Jugend' if kind == 'youth' else 'Erwachsene'
            row = event_model.query.filter_by(zielgruppe=target).filter(
                event_model.datum >= date.today().isoformat()).order_by(
                event_model.datum, event_model.uhrzeit, event_model.id).first()
            if row is None:
                return dict(answer='Im Vereinskalender steht kein bevorstehender Termin für deinen Bereich.', source='portal', data=None)
            data = dict(date=row.datum, time=row.uhrzeit, title=row.titel, place=row.ort)
            answer = f'Der nächste Termin ist {row.titel} am {row.datum} um {row.uhrzeit}.'
        return dict(answer=answer, source='portal', data=data)

    @bp.post('/tool')
    def tool():
        authorize_post()
        value = body()
        if set(value) != {'tool'} or not isinstance(value['tool'], str) or value['tool'] not in ('last_training', 'next_event', 'progress', 'badges'):
            abort(400)
        with lock:
            return jsonify(read_tool(current(), value['tool']))

    @bp.post('/chat')
    def chat():
        authorize_post()
        value = body()
        if (set(value) != {'text', 'external_consent'} or not isinstance(value['text'], str)
                or not 1 <= len(value['text'].strip()) <= 300 or type(value['external_consent']) is not bool):
            abort(400)
        text = value['text'].strip()
        with lock:
            member = current()
            sid = session['adler_portal_sid']
            state = records[sid]
            if state['busy']:abort(409)
            selected = intent(text)
            if selected:return jsonify(read_tool(member, selected))
            greeting = local_greeting(text, profile(member)['display_name'])
            if greeting:return jsonify(answer=greeting, source='local')
            if provider is None:
                return jsonify(answer='Ein freies KI-Gespräch ist noch nicht freigeschaltet. Dein Training, Fortschritt, Termine und die angebundenen Abzeichen kann ich bereits im Portal nachsehen.', source='unavailable')
            if not value['external_consent']:
                return jsonify(answer='Für freie Gespräche muss die unten erklärte KI-Verarbeitung zuerst erlaubt sein. Deine Portalfragen bleiben lokal möglich.', source='consent_required')
            # Never send profile, QR token, results, dates of birth or tool answers.
            messages = [*state['history'], {'role':'user', 'content':text}][-7:]
            if not inference_slots.acquire(blocking=False):abort(503)
            state['busy'] = True
        try:
            answer = provider.reply(messages)
            if not isinstance(answer,str) or not answer.strip():raise Unavailable()
            answer = answer.strip()[:1200]
        except Exception:
            with lock:
                if records.get(sid) is state:state['busy'] = False
            return jsonify(answer='Die KI antwortet gerade nicht. Bitte versuche es später noch einmal. Dein Portal funktioniert weiter.', source='unavailable'), 503
        finally:
            inference_slots.release()
        with lock:
            # Slow replies cannot outlive logout, token rotation, role change or close.
            current()
            if records.get(sid) is not state:abort(401)
            state['history'] = [*messages, {'role':'assistant','content':answer}][-6:]
            state['busy'] = False
            schedule_cleanup()
        return jsonify(answer=answer, source='model')

    @bp.get('/avatar.webp')
    def avatar():
        encoded = (Path(__file__).parent / 'static/art/adler-atlas.webp.base64').read_bytes()
        return Response(base64.b64decode(encoded, validate=False), mimetype='image/webp')

    @bp.post('/close')
    def close():
        # Revocation remains possible even after reaching the chat request quota.
        authorize_post(limit=False)
        with lock:
            sid = session.get('adler_portal_sid')
            if isinstance(sid, str) and hmac.compare_digest(sid.encode(), request.headers.get('X-Adler-Binding', '').encode()):
                records.pop(sid, None)
                session.pop('adler_portal_sid', None)
        return jsonify(closed=True)

    def panel():
        token = (request.view_args or {}).get('token')
        if (not request.endpoint or not request.endpoint.startswith(('jugend_', 'erwachsen_'))
                or not isinstance(token, str) or len(token) < 24 or session.get('betreuer')):
            return Markup('')
        kind, member = resolve(token)
        if (request.endpoint.startswith('jugend_')) != (kind == 'youth'):return Markup('')
        if not session.get('adler_portal_csrf'):
            session['adler_portal_csrf'] = secrets.token_urlsafe(32)
        g.adler_panel_rendered = True
        # Token is already in the existing route; never duplicate it in HTML/URLs.
        return Markup(render_template('portal_adler/panel.html', csrf=session['adler_portal_csrf'],
            display_name=profile(member)['display_name'], dialogue_available=provider is not None,
            dialogue_processor=app.config.get('ADLER_DIALOGUE_PROCESSOR_NOTICE', 'vom Betreiber konfigurierter KI-Anbieter')))

    @app.after_request
    def panel_headers(response):
        if getattr(g, 'adler_panel_rendered', False):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    app.register_blueprint(bp)
    app.jinja_env.globals['ki_adler_panel'] = panel
    # Identity metadata expires on each API request. Conversation content is also
    # purged by one lightweight timer, even if no further requests arrive.

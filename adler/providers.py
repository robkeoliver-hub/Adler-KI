"""Provider receives bounded synthetic conversation only; never a DB handle."""
import json
import urllib.request
import urllib.error
from typing import Protocol

SYSTEM = ('Du bist KI-Adler, ein freundlicher deutschsprachiger Vereinsassistent. '
          'Antworte kurz in höchstens drei kindgerechten Sätzen. Alle Daten sind erfundene Demo-Daten. '
          'Erfinde keine Ergebnisse oder Termine. Keine Waffenbedienung, Modifikationen oder gefährlichen Anleitungen; '
          'verweise für praktische Übungen an die qualifizierte Aufsicht. Du hast keine Werkzeuge und keinen Datenbankzugriff.')

class ProviderError(Exception):
    pass

class Provider(Protocol):
    def reply(self, messages: list[dict]) -> str: ...

class MockProvider:
    def reply(self, messages):
        text = messages[-1]['content'].lower()
        if any(x in text for x in ['waffe', 'abzug', 'munition', 'schießen lernen']):
            return 'Praktische Übungen besprichst du bitte mit deiner Aufsicht im Verein. Ich helfe dir gern, deine Ergebnisse zu verstehen.'
        if 'danke' in text:
            return 'Gern! Möchtest du noch deine Entwicklung oder deine Demo-Abzeichen anschauen?'
        if any(x in text for x in ['nervös', 'aufgeregt', 'angst']):
            return 'Aufgeregt zu sein ist okay. Mach eine Pause und sprich mit deiner Betreuung. Gemeinsam findet ihr einen entspannten Einstieg.'
        if len(messages) > 1:
            return 'Im Mock-Modus kann ich frei formulierte Fragen noch nicht wirklich verstehen. Teste meine Demo-Ergebnisse oder schalte für echte Gespräche einen freigegebenen KI-Provider ein.'
        return 'Hallo, ich bin KI-Adler! Im Mock-Modus zeige ich dir erfundene Ergebnisse, Abzeichen und Termine. Ein echtes Sprachmodell kann dein Verein später anschließen.'

class CompatibleProvider:
    def __init__(self, endpoint, model, key):
        self.endpoint, self.model, self.key = endpoint, model, key

    def reply(self, messages):
        body = json.dumps({'model': self.model, 'messages': [{'role': 'system', 'content': SYSTEM}] + messages,
                           'max_tokens': 160, 'stream': False}).encode()
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        req = urllib.request.Request(self.endpoint, data=body, headers=headers)
        # Do not follow redirects that might disclose credentials/conversation.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs): return None
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=12) as response:
                raw = response.read(65537)
                if len(raw) > 65536: raise ValueError('response size')
                value = json.loads(raw)['choices'][0]['message']['content']
                if not isinstance(value, str) or not value.strip(): raise ValueError('response format')
                return value.strip()[:1000]
        except Exception:
            # Never expose provider bodies, keys, URLs or personal prompts in logs/errors.
            raise ProviderError('provider unavailable') from None

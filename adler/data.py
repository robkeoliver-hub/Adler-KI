"""Read-only, allowlisted tools. No production database connection in this demo."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Principal:
    subject: str
    role: str

class DemoData:
    def snapshot(self, principal):
        if principal != Principal('synthetic-youth', 'youth'):
            raise PermissionError('no authorized demo scope')
        return {'synthetic': True, 'results': [
            {'date': '2026-10-14', 'score': 171, 'shots': 20, 'discipline': 'Lichtpunkt Auflage', 'valuation': 'Ganzringe'},
            {'date': '2026-10-07', 'score': 165, 'shots': 20, 'discipline': 'Lichtpunkt Auflage', 'valuation': 'Ganzringe'}],
            'badges': ['Demo-Bronze (erfunden)'],
            'next_training': 'Beispieltermin: 28.10.2026 um 17 Uhr; kein echter Vereinstermin.'}

    def answer(self, principal, question):
        q = question.lower()
        if not (any(s in q for s in ['ich', 'mein', 'mir']) and any(s in q for s in ['training', 'geschossen', 'besser', 'ergebnis', 'abzeichen', 'ringe']) or any(s in q for s in ['wann', 'nächste']) and any(s in q for s in ['training', 'termin'])):
            return None
        data = self.snapshot(principal)
        if 'abzeichen' in q:
            return 'Dein erfundenes Demo-Profil hat das Abzeichen Demo-Bronze. Echte Vereinsabzeichen werden hier nicht abgerufen.'
        if any(s in q for s in ['wann', 'nächste', 'termin']): return data['next_training']
        if 'besser' in q:
            return 'Im Demo-Profil sind es zuletzt 171 statt 165 Ringe: 6 Ringe mehr bei gleicher Disziplin, Schusszahl und Wertung. Zwei Ergebnisse allein zeigen noch keinen sicheren Trend.'
        return 'Im erfundenen Demo-Training am 14.10.2026 waren es 171 Ringe bei 20 Schuss Lichtpunkt Auflage (Ganzringe).'

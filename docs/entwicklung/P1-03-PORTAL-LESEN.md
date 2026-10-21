# Erster Portaladapter: eigenes letztes Training und Jugendkalender

## Umfang und Grenzen

Dieser PR erweitert die bestehende Flask-Anwendung als optionales Paket
`portal_adler`. Er ist keine zusätzliche Vereinsverwaltung und startet keinen
weiteren Server. Die bisherige Demo auf 5057 bleibt unverändert. Noch kein
Deployment, keine Migration und keine Änderung der hochgeladenen Originaldateien.
Die vorher dokumentierte Analyse steht in PORTALEXPORT-BESTAND.md.

Implementiert:

- Panel zusätzlich zum vorhandenen Basistemplate, geschlossen beim Laden;
- Identität aus geprüftem vorhandenem QR-Bearer statt frei gewählter Benutzer-ID;
- lokale, parametrisierte ORM-Abfragen für ausschließlich eigenes letztes Ergebnis
  und den nächsten Jugendtermin aus der maßgeblichen Termin-Tabelle;
- Revalidierung von Aktivstatus/Tokenrotation, absolute 15-Minuten-Bindung,
  Widerruf bei bestehendem Betreuerlogin/Logout, Schutz vor veralteten Tabs;
- HTTPS-Origin/CSRF, 2-KiB-API-Limit, begrenzte Rate-Limit-/Grant-Speicher,
  sichere generische Fehler, no-store/no-referrer, keine Inhaltsprotokolle;
- Textfeld und zwei direkte Schaltflächen; eng begrenzte Fragezuordnung, **kein LLM**;
- freiwillige deutsche Browserspracheingabe, Textfallback, Vorlesen/Replay/Stop;
  getippte Fragen bleiben stumm, beim Sprechen wird Erkennung beendet;
- Schließen/Escape/Seite ausblenden beendet Mikrofon, Audio und Browseranfragen,
  leert sichtbaren Verlauf und widerruft die Bindung nach Möglichkeit.
  Nach 15 Minuten wird das Panel automatisch geschlossen und der Verlauf geleert.

Kein Versand an einen KI-Anbieter. Browser-Spracherkennung kann ihrerseits einen
Browserdienst verwenden; das Panel weist vor Aktivierung darauf hin. Ohne passende
API bleibt es bei Text. Keine Garantie für iOS-Erkennung oder Autoplay nach einer
Netzwerkantwort: Replay wird ausdrücklich per Tipp ausgelöst. Noch keine echte
männliche Wunschstimme, Stimmenauswahl oder fertig gestaltete Adleranimation.

Nicht enthalten: öffentlicher Allgemeinchat, Betreuer-Datenwerkzeuge, Abzeichen,
Ergebnisvergleiche, OCR-/Upload-Werkzeuge, RSVP, Schreibaktionen, PWA-Änderung oder
LLM-Provider. Diese Funktionen werden nicht durch erfundene Antworten simuliert.
Der aktuelle gemeinsame Betreuerlogin reicht für zusätzliche KI-Adminrechte nicht.

## Einbindung ausschließlich in eine isolierte Portal-Kopie

Noch keine dieser Änderungen auf dem Produktiv-Pi anwenden. Vor Freigabe: konsistentes
Backup/Restore, sicherer SECRET_KEY, geprüfte Tokenrotation und -Logs, tatsächliche
Proxykette und private Bildablage klären. Nur synthetische Daten für Integrationstests.
Das Export-app.py nicht importieren, solange es auf eine reale DB zeigen könnte:
sein Modulende führt create_all und Schemaänderungen aus.

1. Paket `portal_adler/` neben app.py in die isolierte Quellcodekopie übernehmen.
   Keine neue Datenbank und keinen zweiten Login anlegen.
2. Nach den bestehenden Modell-/Routendefinitionen, **vor** dem vorhandenen
   `with app.app_context():`-Block ergänzen:

```python
from portal_adler import init_portal_adler

app.config.update(
    ADLER_PORTAL_ENABLED=os.environ.get("ADLER_PORTAL_ENABLED", "0") == "1",
    ADLER_PORTAL_TOKEN_REVIEWED=os.environ.get("ADLER_PORTAL_TOKEN_REVIEWED", "0") == "1",
    ADLER_PORTAL_ORIGIN=os.environ.get("ADLER_PORTAL_ORIGIN", ""),
)
init_portal_adler(
    app,
    youth_model=Jugendlicher,
    training_model=Training,
    event_model=Termin,
)
```

3. In `templates/base.html` unmittelbar vor `</body>` genau diesen zusätzlichen
   Aufruf ergänzen. Keinen vorhandenen Menü-/Formular-/Skriptblock ersetzen:

```jinja2
{{ ki_adler_panel() }}
```

4. Standardmäßig deaktiviert lassen. Erst im isolierten Test nach Sicherheitsprüfung
   ADLER_PORTAL_ENABLED=1 und ADLER_PORTAL_TOKEN_REVIEWED=1 setzen. Das zweite Flag
   ist eine bewusste Freigabe der vorhandenen Bearer-Authentifizierung, keine
   automatisch bewiesene Sicherheit. Origin ist z.B. https://portal-test.example
   ohne Pfad/abschließenden Slash. Bestehende Flask-Konfiguration benötigt
   SECRET_KEY mit mindestens 32 Zeichen (niemals REDACTED_FOR_CODEX), Secure und
   HttpOnly sowie SameSite=Lax oder Strict. Keine Secrets in Git speichern.

Die Erweiterung bleibt im selben Waitress-Prozess wie die Portal-App und verwendet
keinen HTTP-Aufruf zur Demo auf 5057. Ein Prozess ist erforderlich: flüchtige Grants
sind pro Prozess. Mehrere Worker/Instanzen werden nicht unterstützt (kein externer
Sessionstore in diesem Schritt). Bei Neustart müssen Panels neu geöffnet werden.
Es gibt keinen Hintergrundprozess, kein Audio-/Chatarchiv und keine Modelllast.

Maximal 256 Bindungen, 512 Rate-Limit-Buckets; pro IP maximal 30 POSTs/Minute.
Gemeinsame Vereins-IP teilt das Limit. Abgelaufene Grant-Metadaten werden bei der
nächsten API-Anfrage aufgeräumt; sie enthalten keine Namen oder Chattexte. Zugriff
ist ab exakt 900 Sekunden gesperrt, ohne Verlängerung durch Folgeanfragen.
Browserabbruch garantiert keine Beendigung einer bereits laufenden SQL-Abfrage;
die festen Lesefunktionen bleiben deshalb kurz und eng begrenzt. Keine späten
Antworten werden nach Schließen angezeigt/gesprochen. Widerruf über Netzwerk ist
best-effort; absolute Ablaufprüfung schützt auch bei Verbindungsabbruch.

## Tests

```bash
python3 -m venv .venv-test
.venv-test/bin/python -m pip install -r requirements-portal-tests.txt
.venv-test/bin/python -m pytest -q
```

125 Tests bestanden in der Cloud (98 bisherige, 27 neue Portaltests) mit Python 3.12,
Flask 3.1.3, Flask-SQLAlchemy 3.1.1 und SQLAlchemy 2.0.44. Synthetische SQLite-
In-Memory-DB, Jugend A/B, Aktivstatus, Rotation, Betreuerwechsel, Logout, CSRF/Origin,
15-Minuten-Ablauf, veralteter Tab, Datenisolation, Kalender, leere Bestände, Limit-
und Fehlerfälle. SQL-Ereignisprüfung bestätigt ausschließlich lesende Statements.

Optionaler Browser-Smoke (nur Entwicklungsrechner, nicht auf Pi installieren):
Playwright installieren, passenden Chromium herunterladen, dann
`python tests/browser_portal.py`. Alternativ CHROMIUM_EXECUTABLE auf vorhandenes
Chromium setzen. Chromium mit 375/1280 Pixeln geprüft: Text stumm, Replay, simulierte
Spracheingabe, Stop beim Schließen, Escape, fehlende Speech-API und additive
synthetische Navigation. Speech-APIs sind dabei simuliert, kein echter Anbieter.
Zusätzlich wurde das tatsächliche exportierte base.html mit der echten Jugendnavigation
lokal gerendert: Nach Entfernen des hinzugefügten Panels war das bisherige HTML
identisch. app.py wurde dabei weder importiert noch verändert. Das ist keine vollständige Regression
aller realen Portalrouten. Echter iPhone-/Android-/Pi-Test und Sprachqualität offen.

## Rollback

ADLER_PORTAL_ENABLED=0 lässt alle neuen API-Routen und Panelmarkup entfallen,
sofern die normale spätere Dienstumschaltung freigegeben wurde. Keine Datenmigration
zurückzunehmen. Vollständige Rücknahme: Templateaufruf und init-Aufruf entfernen,
Paket entfernen. Noch keine Anleitung zur Produktivschaltung: reale Portalregression,
Backup/Restore und Betreiberfreigabe sind davor erforderlich.

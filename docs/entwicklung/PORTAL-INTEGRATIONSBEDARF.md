# Konkret fehlende Dateien für die echte Portal-Integration

Im Repository Adler-KI liegt nur die isolierte Demo. Die frühere Portal-ZIP ist vorhanden und statisch geprüft, ihr Gleichstand mit dem laufenden Portal ist nicht bestätigt. Deshalb werden keine Ersatz-Mitgliederverwaltung, keine neuen echten Benutzerkonten und kein paralleler Kalender erstellt. Keine DB-/Auth-/Menüintegration anhand vermuteter Schnittstellen.

Ein Repository-Link samt tatsächlich installiertem Commit oder eine bereinigte aktuelle Quellcodekopie genügt. Keine Passwörter, QR-Tokens, API-Schlüssel, vollständigen Datenbanken, Uploads, privaten Logs oder Mitgliederdatensätze bereitstellen.

## Benötigte Quellen (Namen aus der vorhandenen ZIP)

| Datei / Bereich | Wofür benötigt |
| --- | --- |
| `app.py` und alle daraus importierten eigenen Pythonmodule; falls aufgeteilt `models.py`, Auth-/Blueprint-/Service-Module | Tatsächliche Flask-App-Factory, Routen, Session-/Login-/Logoutfluss, Aktivprüfung und Rollen ermitteln; DB-Initialisierung beim Import vermeiden. |
| `templates/base.html` | Ein gemeinsamer, optionaler Einhängepunkt neben bestehender Navigation; keine Chatseite als Ersatz. |
| `templates/jugend/_nav.html`, `start.html`, `ergebnisse.html`, `abzeichen.html`, `termine.html`, ggf. `training.html` und neue Jugendseiten | Menü- und Formularregression für Jugendliche, bestehende Ergebnisse/Abzeichen/Kalender weiter normal bedienbar. |
| `templates/erwachsene/_nav.html` und die aktuellen Unterseiten; `templates/betreuer/_nav.html`, `login.html`, `dashboard.html` und aktuelle Verwaltungsseiten | Rollenabhängige Menüs sowie bestehende Upload-/Bearbeitungsfunktionen erhalten. |
| `static/css/style.css`, alle aktuellen eigenen `static/js/*.js`, insbesondere `member-rewards.js` und Navigation | CSS-/DOM-/Ereigniskollisionen, responsive Layout, ein-/ausblendbares Adlerpanel ohne kaputte Buttons. |
| `static/pwa/service-worker.js`, Manifest-Erzeugung (bisher in app.py), ggf. weitere PWA-Dateien | Private Seiten/API niemals offline speichern; bestehende Origin-Caches nicht pauschal löschen; Installierbarkeit/iOS prüfen. |
| `meyton_ocr.py` und Upload-/Speicherhelfer | Bestehenden OCR-/Bestätigungsablauf und private Uploadpfade unverändert lassen. |
| `requirements.txt`, ggf. Lockdatei, vorhandene Migrationen und Startskript/Service-Vorlage | Abhängigkeiten/Import-Nebeneffekte, Teststart ohne produktive DB und portables Packaging prüfen. |

Zusätzlich ausschließlich bereinigte Betriebsinformationen: maßgebliche Nginx-`server`-/`location`-/`upstream`-/`proxy_set_header`-Abschnitte für Portal und Demo; aktive systemd-Unit ohne Secretwerte; Python-/Flask-/SQLite-Versionen; reines SQL-Schema mit Indices/Fremdschlüsseln/Migrationsstand. Kein Export von Tabellenzeilen. Es wird hier weder ein Befehl auf dem Pi ausgeführt noch ein Zugriff eingerichtet.

## Authentifizierung vor echten Daten

ZIP-Befund: persönliche QR-Bearer-Tokens im Pfad, Aktivprüfung und token_urlsafe(24); Betreuung über gemeinsames Passwort und betreuer=True-Session. Keine nachgewiesenen individuellen Betreuerscopes. Diese Befunde müssen am aktuellen Code bestätigt werden. Eine Benutzer-ID aus Chat/JSON/Client-Rolle ist niemals Berechtigung.

Danach minimale Integration:

1. Bestehende Session wird durch AuthAdapter gelesen, nicht durch neue Konten ersetzt. Subject/Rolle/Scope/Aktivstatus/Sitzungsrevision nur serverseitig. Rollenwechsel widerruft Kontext.
2. Anonymer Zugriff erhält nur freigegebene öffentliche Intents, keinen freien Allgemeinchat oder private Werkzeuge. Ohne verlässliche öffentliche Datenquelle keine Demo-Ergebnisse/Beispieltermine.
3. Jugendliche ausschließlich eigene feste, parametrisierte Lesefunktionen; Betreuung nur bestätigte Gruppen/Felder. Keine automatische Übernahme pauschaler Vollrechte aus einem gemeinsamen Betreuerlogin.
4. Persönliche Ergebnisse/Termine lokal aus bestehenden Quellen beantworten. Keine Übergabe in externen LLM-Verlauf ohne gesonderte Freigabe. Kalender/Abzeichen nicht duplizieren.
5. Adlerpanel optional in base.html ergänzen; vorhandene Menülinks, Formulare und Rollen bleiben Eigentum des Portals. Erst Tests mit Jugend A/B, Betreuung, anonym, deaktiviertem Konto und Rollewechsel, danach isolierte Geräteabnahme.

Der Konfigurationsschritt sperrt deshalb `ADLER_MODE=production` bereits vor Konstruktion von DemoData oder Provider. Das ist ein bewusst sichtbarer Blocker, keine funktionierende produktive Authentifizierung. Ein Demo-Code darf niemals als Zugang zu echten Mitgliederdaten umgedeutet werden.

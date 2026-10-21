# Portalexport: Befund vor Implementierung

Geprüft am 21.10.2026, Archiv-SHA256
536a6a72407b8f6a370e8f294f88d78b0c51de9cdc6e007dcbcedc237f298770.
Das privat bereitgestellte Archiv wird nicht in Git übernommen. 51 Textdateien
wurden technisch geprüft; zusätzlich enthält es ein Vereinslogo. Die beiden
Konfigurationsdefaults sind redigiert. Der literale QR-Wert in app.py:897 ist der
bereits bestätigte Demo-Platzhalter. Kein DB-Archiv enthalten. Musterprüfung und
Sichtung sind keine Garantie der vollständigen Abwesenheit von Geheimnissen;
insbesondere dürfen öffentliche Veröffentlichungen keine Originalquellen enthalten.

## Struktur und Integrationspunkte

Monolithische Flask-App `app.py`, SQLAlchemy, Waitress-Start im Bestand;
`meyton_ocr.py`, gemeinsames `templates/base.html`, Jugend-/Erwachsenen-/Betreuer-
Templates, eigenes CSS/JS sowie `static/pwa/service-worker.js`.
Eine requirements.txt oder effektive Nginx-/systemd-Konfiguration fehlt im Export.
Keine Bestätigung des Proxy-/Dienstzustands oder des tatsächlichen DB-Schemas.

Modelle: Jugendlicher, Erwachsener, Training, ErwachsenenTraining, Abzeichen,
VerliehenesAbzeichen, JugendAbzeichenHinweis, GluecksscheibeRunde,
GluecksscheibeTeilnahme und Termin. Kalender: Termin mit Zielgruppe, Datum und
Uhrzeit; keine vorhandene RSVP-/Anwesenheitstabelle im Export. Keine parallele
Kalenderverwaltung anlegen. Abzeichen kombinieren Regeln und manuelle Vergaben;
keine vereinfachte Ersatzvergabe durch KI.

Jugend-/Erwachsenenrouten unter `/jugend/<token>` bzw. `/erwachsen/<token>` prüfen
QR-Bearer-Token und aktiv=True. Token entstehen mit token_urlsafe(24). Jugend hat
keine bestehende Login-Session. Betreuung: gemeinsames Passwort aus Umgebung,
Sessionfeld betreuer=True; keine individuellen Accounts/Scopes/Sessionrevisionen.
Die neue Funktion darf daraus keine zusätzlichen administrativen Befugnisse ableiten.

Gemeinsames base.html ermöglicht genau einen ergänzenden Templateaufruf, ohne
bestehende Menülinks/Formulare zu ersetzen. Portaladapter muss in derselben Flask-
Anwendung laufen: Die separate Demo auf 5057 besitzt keine Portal-Authentifizierung.

## Sicherheitsbefunde und Sperren

- Import von app.py führt create_all und direkte ALTER-TABLE-Anweisungen aus.
  Nicht gegen Produktionsdaten importieren; neuer Adapter importiert app.py nie.
- URL-Bearer können in Browserchronik, Server-/Proxylogs und Referern landen.
  Zusätzlicher Zugriff nur nach ausdrücklicher Sicherheitsprüfung der bestehenden
  Tokenverwaltung; langfristig einmaligen QR-Austausch gegen widerrufbare Session
  statt dauerhafter Tokens in sämtlichen URLs vorbereiten.
- REDACTED_FOR_CODEX ist nur im Export ein Ersatzwert. Die bisherigen Prüfungen
  verwerfen ihn nicht automatisch; neue Integration verweigert diesen Secretwert.
- Cookie Secure hängt im Bestand von COOKIE_SECURE ab; neuer Adapter benötigt Secure.
- Kein zentraler CSRF-Schutz im Export erkennbar. Bestehende Schreiboperationen nicht
  über KI zugänglich machen. Neue API erhält Origin-/CSRF-Prüfung.
- Gemeinsames Betreuerlogin erlaubt keine nachweisbare individuelle Autorisierung/
  Revision. Keine Betreuer-Datenwerkzeuge oder KI-Schreibfunktionen in diesem Schritt.
- OCR hat bestehende Vorschau und manuelle Speicherung; Originaldatei wird nach OCR
  gelöscht. Zielbild-Ausschnitte liegen unter static/uploads/targets; sie können
  personenbezogene Inhalte enthalten. Upload-Decoding, Privatablage, Berechtigung
  und Löschfrist prüfen, bevor Bilder über KI verarbeitet werden.
- Service Worker löscht beim Aktivieren alle anderen Origin-Caches und cached beliebige
  GETs unter /static/. Keine neue PWA registrieren; KI-API/HTML konsequent no-store.
  Bestehende Cachebereinigung ist vor gemeinsamer PWA-Abnahme zu begrenzen.
- ProxyFix vertraut einem Proxy für Host/Proto/For. Tatsächliche Proxykette fehlt;
  neue API verwendet explizit konfigurierte HTTPS-Origin statt Clientrollen/Hostannahmen.

## Erster kleiner Schritt

Opt-in-Paket `portal_adler`: bestehende Modelle werden als Referenzen injiziert,
keine neue Datenbank/Benutzerverwaltung. Keine Migration, kein ORM-Commit, kein
externer Anbieter, kein Chat-/Audio-Archiv. Feste Nur-Lese-Werkzeuge für eigenes
letztes Training und nächsten Jugendtermin. Identität wird nach QR-Prüfung serverseitig
gebunden, bei jeder Anfrage auf Aktivstatus und Tokenrotation geprüft; keine
frei übergebene Benutzer-ID. Session endet spätestens nach 15 Minuten absolut.
Begleitendes Panel ist zusätzlich über Templatehelfer einhängbar; deaktiviert
bleiben Routen und Markup vollständig abwesend. Echte Portalregression und Pi-
Installation erfolgen erst nach Freigabe, nicht durch diese Entwicklung.

# Analyse vor Implementierung – 21.10.2026

Alle 64 ZIP-Einträge inventarisiert; sämtliche Textdateien eingelesen, Python-Struktur statisch ausgewertet. SHA-256 und Größen in archive-inventory.json; Routen und Modellfelder in INVENTAR.md. Keine Datenbank in der ZIP, keine echten Konten oder Laufzeitkonfiguration überprüfbar. Original nicht ausgeführt, nicht importiert und nicht verändert.

## Aufbau und Integration
Eine monolithische app.py (Flask, SQLAlchemy/SQLite), Jinja-Templates für Jugend, Erwachsene und Betreuer, OCR/Pillow, Waitress, PWA-Service-Worker. Zehn Modelle: jugendlicher, erwachsener, training, erwachsenen_training, abzeichen, verliehenes_abzeichen, jugend_abzeichen_hinweis, gluecksscheibe_runde, gluecksscheibe_teilnahme, termin. Stammdaten enthalten Namen, Geburtsdaten und Ausrüstungsnotizen. Trainings verknüpfen Mitglied und Ergebnisse. Abzeichen sind komplexe, teils berechnete Regeln; nicht nur ein einzelnes Feld am Mitglied.

Routenfamilien: / und /demo/jugend*, /jugend/<token>*, /erwachsen/<token>*, /betreuer/*, /kontakt-downloads, /service-worker.js. Jugendliche lesen eigene Ergebnisse/Abzeichen/Termine über QR-Token; Erwachsene können zudem Ergebnisse ändern und hochladen. Betreuer verwalten Mitglieder, Training, OCR, Abzeichen und Termine. Exakte Routen im Inventar.

Design: dunkles Blaugrün, Lime #c6f36a, Goldakzente, Karten, mobile Navigation, Inter/Barlow. Demo übernimmt Farben und Formsprache mit Systemschriften, eigenem SVG und ohne externe Assets. Bestehende Google-Fonts werden nicht eingebunden.

## Sicherheitsbefunde
- Hohe Priorität: app.py führt ab Zeile 2232 beim Import db.create_all, Seeds und ALTER TABLE aus. Kein Import für die Demo; keine Migration und kein produktiver Serverstart.
- QR-Tokens: secrets.token_urlsafe(24), eindeutig und aktiv=True geprüft. Gute Entropie, aber dauerhaftes Bearer-Geheimnis im URL-Pfad, im Klartext in SQLite. Weitergabe, Browserchronik, Proxy-/Zugriffsprotokolle, QR-Export und Referer können Zugang offenlegen. Rotation über Betreuer möglich; keine erkennbare zeitliche Gültigkeit, zusätzliche PIN oder individuelle Jugendsitzung. Kein hinreichender alleiniger Zugang für neue sensible KI-Schnittstellen.
- Betreuer: gemeinsames Umgebungs-Passwort (constant-time Vergleich), signiertes Session-Cookie mit betreuer=True, keine individuellen Accounts oder feinen Rollen. Keine erkennbaren Login-Ratenlimits, CSRF-Tokens oder explizite kurze Sitzungsdauer. SECRET_KEY erforderlich; Secure-Cookie nur bei COOKIE_SECURE=1.
- ProxyFix vertraut einem Proxy inklusive Host/Forwarded-For: nur hinter kontrolliertem Proxy sicher; Backend darf nicht direkt erreichbar sein.
- Uploads unter static/uploads: Schutz hochgeladener personenbezogener Belege separat prüfen; Dateiname ist keine Zugriffskontrolle. Originale Fehler-/Proxylogs und produktive TLS-Konfiguration nicht in ZIP verifizierbar.
- ORM-Abfragen verwenden weitgehend gebundene Werte. Dynamische ALTER-Texte nutzen interne Spaltenlisten, sind aber unerwünschte Import-Schreibzugriffe. Die KI erhält keinen SQL-Zugang.
- Externe Schriften und eventuell browserseitige Spracherkennung können Dritte kontaktieren. Demo lädt keine Drittressourcen und schaltet Sprachdienste erst nach ausdrücklicher Bestätigung im UI frei.

## Entscheidung vor Änderungen
Neue separate Anwendung auf Port 5057, eigenem Zugangscode und eigener kurzlebiger serverseitiger Sitzung. Ausschließlich synthetische Daten; weder DB-Pfad noch produktive Tokens konfigurierbar. Produktive Originaldateien bleiben außerhalb des Lieferpakets. Allgemeiner Dialog über austauschbaren Provider; Mock ist ausdrücklich Simulation, kein Sprachmodell. Echte KI optional über einen selbst gehosteten, getrennten OpenAI-kompatiblen HTTPS-Endpunkt, nur nach Betreiberfreigabe für synthetischen Testbetrieb. Keine Zusage kostenloser Kontingente.

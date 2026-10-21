# Konkreter Implementierungsplan / Abhängigkeiten

Diese Liste setzt die Reihenfolge des Auftrags um. „Geplant“ ist kein implementiertes Feature. Alle Schritte zunächst isoliert; Zielhoständerungen nur nach Freigabe. PRs klein halten, bestehende Menüs sind verbindliches Regressionskriterium.

| Ticket | Priorität / Status | Abhängigkeit | Kleiner Lieferumfang / Abnahme |
| --- | --- | --- | --- |
| P0-01 | P0 / geprüft | keine | PR-/Branch-/Blobabgleich, Original-ZIP statisch, öffentliche GET-Prüfung, 25 Basistests. Befunde in BESTAND dokumentiert. |
| P0-02 | P0 / offen, Zugriff fehlt | aktuelle Portal-Codebasis und freigegebene lesende Betriebsinfos | Aktuellen Commit, effektive Nginx-/systemd-Konfiguration, tatsächliches Schema (keine Datensätze) und Authfluss verifizieren. Keine Secrets oder Kinderdaten anfordern/publizieren. |
| P0-03 | P0 / geplant | P0-02 | Konsistente SQLite-/Upload-/Konfigurationsbackups, Restore-Test in isolierte Kopie, Migrationsversionierung ohne Import-Schreibeffekte; keine Produktivmigration. |
| P1-01 | P0 / implementiert in offenem PR #2 | P0-01 | Sitzungswiderruf löscht Kontext referenzsicher; keine späten Antworten nach Logout/Neuanmeldung/Ablauf/Principalwechsel; keine 30-s-Ablaufverlängerung; Tests ohne lange Sleeps. Bestehender fester 15-Minuten-Login bleibt. |
| P1-02 | P0 / implementiert, separat geprüft | P1-01 | Konfiguration mit validierten ADLER_*-Umgebungsvariablen, dokumentierter INI-Kompatibilität, produktiver Modus lehnt DemoData/Mock implizit ab. Fehlender Auth-/Datenadapter endet geschlossen; keine synthetischen Daten als Produktionsfallback. Tests für jeden Startmodus und Windows-Pfade. |
| P1-03 | P0 / blockiert | P0-02, P1-02 | Einheitlichen AuthAdapter an bestehende Session anbinden, individuelle Rollen-/Scope-Matrix, sichere Tokenübergabe ohne URL-/Log-Leck; keine Schattenkonten. Jugend A/B, Betreuung, anonym, deaktiviertes Konto, Rollenwechsel, CSRF und Sessionrevision testen. |
| P1-04 | P0 / blockiert | P1-03 | Feste lesende Tools für eigene Ergebnisse/Abzeichen und maßgeblichen Kalender, Altersgruppen lokal, keine fremden Namen. 2 Jugendprofile mit klar verschiedenen Daten, gemischte Disziplin/Wertung und Ausfallfälle prüfen. |
| P1-05 | P1 / UI-Vorbereitung geprüft, echte Einbettung blockiert | P0-02, P1-03 | Einklappbares Adlerpanel plus große Ansicht in bestehenden Templates/Blueprint. Vollständige Menü-/Formularnavigation mit KI an/aus und ohne Providerfehlerbeeinflussung. Kein ersetztes Portalmenü. |
| P1-06 | P0 / blockiert vor externer Nutzung | Anbieterauswahl/AVV-Prüfung, P1-03/04 | Freier LLM-Dialog optional nach Datenfreigabe, Datenschutz-/Kostenblatt, getrennte öffentliche Allowlist ohne offenen Allgemeinchat, typed Tool-Dispatcher. Keine persönlichen Toolantworten in externem Verlauf; Injection-Tests (Dokument/Foto/Webseite/Chat), Schema/Scope/Outputgrenzen und echte Providerfehler. Keine Gratis-Kontingente erfinden. |
| P1-07 | P1 / geplant | lizenzierte/eigene Avatarbasis, P1-05 | Freundlicher SVG-Adler und Zustände, Animation aus/Reduced Motion, auswählbare deutsche Systemstimme/Replay, Stop/Mute, kontrolliertes Halbduplex, optionaler Folgedialog mit Tap-Fallback. Echte iPhone-TTS-Abnahme plus Android, typed bleibt stumm. |
| P1-08 | P1 / geplant | P0-02, P1-05/07 | Gemeinsame PWA ohne privaten Offlinecache, Cache-Namensräume isolieren, Manifest/Update/Offline-Seite. Installiertes iPhone und Android testen; keine doppelte Cachebereinigung/Tokenpersistenz. |
| P2-01 | P1 / geplant | P0-03, P1-03/04 | Bestätigungsmechanismus mit Ablauf, Actor-/Ressourcenrevision, Idempotenz; eigene RSVP per Menü/Sprache und Betreuer-Anwesenheit. Keine Teilnehmernamen für Jugend. Test: fremde/abgelaufene Bestätigung, Rollenwechsel, Kalenderkonflikt, Rücknahme. |
| P2-02 | P1 / geplant | P2-01, P1-08 | Opt-in-/Ruhezeit-Reminder; Absage/Verschiebung nur nach Betreuerbestätigung. Keine Pushes nach Abmeldung; doppelte/alte Zustellungen und generische Sperrbildschirmtexte testen. |
| P2-03 | P1 / geplant | P0-03, P1-03, bestätigte Vereinsregeln | Quizentwürfe → Betreuerprüfung → Veröffentlichung, freiwillige Challenges/XP/Level ohne Ringzahlbelohnung/Streakdruck/Ranking; offizielle Abzeichen getrennt. Test Freigabe, Alter, erneute Bewertung/Idempotenz und deaktivierter Inhalt. |
| P3-01 | P2 / geplant | P2-01/03 | Editierbare/druckbare Trainingspläne und Faktenbericht-Entwurf nach abgeschlossener Anwesenheit; keine freie Betreuernotiz-Sprachspeicherung. Nie Teilnehmerzahl/Erfolg erfinden. |
| P3-02 | P1 / geplant | P0-03, P1-03, vorhandene OCR geprüft | Upload-Limits, MIME/Decoding/Metadaten-/Pfadprüfung, private Speicherung und Löschfrist, OCR-Konfidenz/Korrekturmaske; Speichern erst manuell bestätigt. Test Fake-Bilder, zu große Bilder, Traversal, unsichere/berichtige Felder und Berechtigungen. |
| P3-03 | P1 / geplant | P2-01-Bestätigung, P3-02 | Fotos/Beiträge/Webseitenentwürfe; dokumentierte Personenfreigaben, unbekannt=gesperrt, Vorschau/Bestätigung/Revisionsprüfung, Audit ohne Chat und Restore. Kein autonomes Publizieren/keine Gesichtserkennung. |
| P4-01 | P2 / geplant | P0-02/03, separate Hostfreigabe | Nur-lesendes Monitoring mit Allowlist, Warnungen statt Eingriffe; Links/Termine/mobile Ansicht und CPU/RAM/Disk/DB. Updates/Migrationen/Neustarts/Löschungen benötigen gesonderte Freigabe. |
| P4-02 | P2 / geplant | funktionale Basis | Pi-3-Last-/Latenz-/Sicherheitsmessung und Windows-Installation/Backup/Restore; Ressourcenbudget aus Messung, nicht aus Vermutung. |

## Nächste konkrete Reihenfolge

P1-01 nach Analyse implementieren und lokal prüfen → Folge-PR gegen Demo-Branch, kein Merge. Parallel fehlenden Portalstand/Assets klären. Danach P1-02 (Umgebungsvariablen und Startmodus-Sperren) als eigenständiger PR. P0-02/03 müssen vor echter Auth-/Datenintegration abgeschlossen sein. Keine Umgehung durch Demo-Zugangscode mit echten Daten. Phase 1 gilt erst nach P1-02 bis P1-08 und den realen Rollen-/Gerätetests als abgeschlossen.

## Freigabe- und Testregeln

Jeder PR enthält Setup, Änderung, Tests, fehlende Nachweise, Migrationsstatus und Rollback. CI/Cloudtests ersetzen keine Pi-/Safari-Abnahme. Änderungen am Zielsystem, Schema, Sicherheitskonfiguration oder produktiven Diensten benötigen die ausdrücklich zusätzliche Freigabe des Betreibers. Die Erlaubnis zum GitHub-PR ist keine Deploymenterlaubnis. Keine Features aus Phasen 2–4 in diesen kleinen Schritt ziehen.

## Aktualisierung nach P1-02

Mergeabhängigkeiten #1/#2 sind geprüft und ihre Beschreibungen vorbereitet; beide bleiben offen. P1-02 ist implementiert (74 Tests), Produktivstart blockiert vor DemoData/Provider. Siehe MERGEPLAN.md, P1-02-KONFIGURATION.md und PORTAL-INTEGRATIONSBEDARF.md. P0-02, P1-03 und P1-04 bleiben mangels verifiziertem aktuellem Portal-Code blockiert; kein Zugriff über den Demo-Code auf echte Daten. Als unabhängige Vorbereitung ist nur ein ein-/ausblendbarer Begleiter innerhalb der isolierten Demo zulässig; dies ist noch keine Portal-Einbettung und schließt P1-05 nicht ab.

## Aktualisierung nach Begleiter-Vorbereitung

Ein-/Ausblenden, Stop beim Schließen, Fokus/Escape und das bestehende Gespräch sind in der isolierten Demo geprüft. 76 pytest-Tests und Chromium-Smoke mit zwei Viewports sowie synthetischer Hostnavigation/Formularen mit/ohne JavaScript bestanden. Das schließt P1-05 nicht ab: tatsächliche Portalmenüs und gemeinsame Authentifizierung bleiben ohne aktuelle Portalquellen unprüfbar. Siehe P1-05-BEGLEITER-VORBEREITUNG.md. P1-03/04 bleiben gesperrt statt einer neuen Mitglieder-/Kalenderverwaltung.

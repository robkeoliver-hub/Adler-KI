# Aktueller Integrationsschritt: sichere Portalquellen

## Tatsächlicher Stand am 21.10.2026

PR #1–#5 wurden in ihrer Abhängigkeitsreihenfolge geprüft und mit Merge-Commits
nach `main` übernommen. Vorher bestanden die 98 Tests des gemeinsamen Standes.
Der Dateibaum des Ergebnisses entspricht dem geprüften Installer-Branch.
Es wurde kein Raspberry-Pi-Dienst aktualisiert, kein Proxy geändert und keine
Produktivdatenbank geöffnet. Der Betreiber hat die Aktivierung der bestehenden
Demo auf 5057 per Terminalausgabe bestätigt; das ist keine Bestätigung für echte
Portalrollen, Mitgliederdaten, Sprache oder einen freien LLM.

Der nächste kleine PR ergänzt ausschließlich ein eigenständig ausführbares
Nur-Lese-Werkzeug für P0-02. Es ist keine zweite Vereinsverwaltung und keine
weitere Demo. Bestehende Anwendung und Installer bleiben unverändert.

## Einmalige lokale Vorprüfung auf dem Pi

Als `pi` im Terminal ausführen, nicht als root; kein Neustart nötig:

```bash
curl -fL https://raw.githubusercontent.com/robkeoliver-hub/Adler-KI/ki-adler/portal-export-pruefung/scripts/check_portal_export.py -o /home/pi/check_portal_export.py
python3 /home/pi/check_portal_export.py /home/pi/ki-adler-portal-export.zip
```

Das Werkzeug benötigt nur die Python-Standardbibliothek. Es öffnet ausschließlich
das angegebene ZIP, extrahiert und importiert nichts und verändert keine Dateien.
Es führt keinen Netzwerkaufruf aus. stdout enthält nur Anzahl geprüfter Dateien,
Eintragsnummern und Befundcodes, niemals Dateinamen, Quelltext oder Secretwerte.
Exit 0 bedeutet lediglich keine erkannten technischen Befunde; Exit 2 bedeutet
Prüfbedarf. `manual_review_required` bleibt **immer true**. Kein automatisches
Hochladen, Freigeben oder Bereinigen.

Prüfungen: Archiv-/Dateigrößen, Pfade, Duplikate, Symlinks, verschlüsselte Dateien,
private Laufzeitordner, Konfigurationen, Datenbankdateien einschließlich WAL/SHM,
SQLite-Signatur trotz umbenannter Datei, bekannte Credential-Muster und literale
Schlüssel/Passwörter, SQL-Datenexporte und nicht geprüfte Dateitypen.
Auch das Vereinslogo kann `unreviewed_file_type` auslösen: Bilddateien benötigen
separate Sicht-/Lizenz-/Metadatenprüfung und sind für die Codeanalyse nicht nötig.
`REDACTED_FOR_CODEX` wird als Platzhalter erkannt, ist aber keine Freigabe des Exports.

**Grenzen:** Reguläre Ausdrücke erkennen nicht alle Geheimnisse oder Personendaten.
Namen, E-Mail-Adressen, Telefonnummern, Tokens in Vorlagen, Kommentare, JSON und
beliebig benannte Schlüssel müssen zusätzlich lokal fachlich geprüft werden.
Auch ein SQL-Schema kann sensible Vorgabewerte enthalten. Keine vollständige
Datenbank, Uploads, Protokolle oder echte Konfigurationen bereitstellen.
Den Export keinesfalls ungeprüft in das öffentliche GitHub-Repository laden.

## Benötigter Integrationsstand

Die vorhandene ältere ZIP dient nur zur statischen Orientierung. Aktuell benötigt:

- `app.py`, alle eigenen Auth-/Modell-/Service-Module und `requirements.txt`;
- `meyton_ocr.py`, Upload- und Bestätigungsrouten;
- `templates/base.html`, Jugend-/Betreuer-Navigation und deren Unterseiten;
- eigene CSS-/JS-Dateien, PWA-Manifest und Service Worker;
- bereinigte Dienst-/Proxy-Konfiguration sowie Schema ohne Tabellenzeilen.

Vollständige Einzelheiten: `PORTAL-INTEGRATIONSBEDARF.md`. Keine Benutzerkonten,
Kalender oder Berechtigungen parallel anlegen. Produktivintegration benötigt
weiterhin ausdrückliche Freigabe nach Tests auf isolierter Kopie.

## Folgende kleine Schritte und Abnahme

1. P0-02: aktuellen bereinigten Export privat bereitstellen und statisch analysieren;
   Login, Logout, Aktivstatus, tatsächliche Rollen und Import-Schreibeffekte prüfen.
2. P0-03/P1-03: Restore auf synthetischer Kopie und AuthAdapter an vorhandene
   Authentifizierung; Jugend A/B, anonym, Betreuer, deaktiviert und Rollenwechsel.
3. P1-05: optionalen Begleiter in vorhandenes Basistemplate einhängen; alle bisherigen
   Menülinks/Formulare mit offenem, geschlossenem und deaktiviertem Adler testen.
4. P1-04: feste lesende Tools für eigene Ergebnisse/Abzeichen und vorhandenen Kalender;
   kein Demo-Fallback, keine freien SQL-Abfragen und keine externe Personendatenübertragung.
5. P1-07: Stimmenauswahl/Replay und freundlichen Avatar ergänzen; männliche deutsche
   Stimme bevorzugen, soweit tatsächlich vorhanden. iPhone-Sprachausgabe real abnehmen.

Autostart bleibt ein eigener Betriebsschritt: zuerst alten Boot-Startmechanismus
ermitteln, dann genau einen Dienst aktivieren. Keine erneute Installation nötig.

## Tests und Rücknahme

119 Tests bestanden in der Cloud mit Python 3.12: 98 bestehende Tests plus 21
Exportprüfungen, darunter manipulierte Archive, Secrets ohne Ausgabe, SQLite-Tarnung,
SQL-Daten, Quellarchive unverändert, keine Extraktion und Konfigurationsliterale.
Kein tatsächlicher aktueller Portalexport lag hier vor; keine Behauptung einer
vollständigen Sicherheitsprüfung oder Bookworm-/iPhone-Abnahme.

Keine Migration, kein neues Paket und kein Deployment. Rücknahme: die beiden
Werkzeug-/Testdateien und diese Dokumentation entfernen; Portal und laufender
KI-Adler sind davon unabhängig.

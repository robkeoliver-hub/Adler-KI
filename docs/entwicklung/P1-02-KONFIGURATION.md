# P1-02: Konfiguration und gesperrter Produktivstart

## Tatsächlich umgesetzt

`adler/config.py` liest validierte Einstellungen ohne Secret-Logging. Priorität: Defaults → optionale alte INI → ADLER_*-Umgebungsvariablen → ausschließlich serverseitige Factory-Overrides (Tests/Einbettung). `run.py` übernimmt die validierten Bind-/Portwerte. Loopback bleibt zwingend. Eine fehlende explizite oder defekte Konfigurationsdatei wird nicht still ignoriert. Explizit leere Umgebungswerte fallen nicht auf alte Schlüssel zurück. INI-Interpolation ist deaktiviert.

`ADLER_MODE=production` verweigert den Start **vor** DemoData, Mock oder externem Provider. Auch API-Key und external_approved können das nicht aufheben. Die echte Portal-Authentifizierung und Datenadapter fehlen noch; daher wird kein angeblich produktiver Betrieb mit erfundenen Daten angeboten. Unbekannter Modus/Provider und ungültige Werte führen zu sicheren Fehlermeldungen ohne Wiedergabe der Konfigurationsinhalte. Beispiel-Zugangscode muss ersetzt werden. Fehlformatierte Unicode-Login-/CSRF-Werte werden generisch abgelehnt, statt einen compare_digest-Serverfehler zu erzeugen.

## Variablen

| Variable | Default / Bedeutung |
| --- | --- |
| ADLER_CONFIG_FILE | Optionaler nativer Dateipfad; alternativ expliziter Factory-Pfad. Ohne Angabe legacy config.ini neben dem Projekt. |
| ADLER_MODE | demo; production derzeit sicher gesperrt |
| ADLER_DEMO_CODE | Eigener ASCII-Zufallscode, mindestens 16 Zeichen; kein eingebauter gültiger Code |
| ADLER_PUBLIC_ORIGIN | http://127.0.0.1:5057; exakte Origin ohne Pfad/Userinfo, HTTPS außerhalb Loopback |
| ADLER_HOST / ADLER_PORT | 127.0.0.1 / 5057; nur Loopback, Port 1–65535 |
| ADLER_SESSION_TTL | 900, maximal 900 Sekunden; feste Demo-Lebenszeit |
| ADLER_PROVIDER | mock oder explizit compatible |
| ADLER_ENDPOINT / ADLER_MODEL / ADLER_API_KEY | Nur serverseitig, Schlüssel optional; HTTPS-Endpunkt ohne URL-Userinfo |
| ADLER_EXTERNAL_APPROVED | false; nur true/false akzeptiert. Schlüssel alleine aktiviert keinen Provider. |

Die bestehende INI und scripts/setup.py bleiben nutzbar. Eine neue Installation kann ohne INI ausschließlich per Umgebungsvariablen konfiguriert werden. Secrets nicht als Git-Dateien oder in Shellhistorie/Logs veröffentlichen; Betreiber nutzt geschützte Dienstkonfiguration. Keine neue Pflicht-API und keine behaupteten Gratiskontingente. Bisherige separate Sprachfreigaben und CSRF-/Ratenlimits bleiben bestehen.

## Setup, Tests, Grenzen

Nur neue isolierte Arbeitskopie: Python-venv, `pip install -r requirements-dev.txt`, `python -m pytest -q`. Ohne echte Secrets können die mitgelieferten Tests vollständig laufen. Anbindung eines externen Dienstes erfolgt nicht durch Tests. Produktivmodus-Sperre ist per env getestet, einschließlich kompatiblem Provider und vorhandenen synthetischen Schlüsselwerten.

74 pytest-Tests bestanden (45 bisherige, 29 zusätzliche). Geprüft: alte INI, Env-/Override-Priorität, env-only, nativer Pfad mit Leerzeichen, fehlende/defekte INI, keine Secret-Ausgabe, sichere Defaults, ungültige URLs/Ports/TTL/Boolean/Modi, Loopback-Bindung, Platzhalter, keine stillen Provideraktivierungen und sichere Ablehnung nicht-ASCII Authwerte. Die Tests isolieren ADLER_*-Variablen, damit eine Entwicklerumgebung keinen Test zu externen Aufrufen umschaltet. Run-Entry-Point mit Stub geprüft, kein echter Server dabei gestartet.

Echter Windows-Start bleibt offen; native pathlib-Pfade sind auf Linux geprüft, kein Windows-Test behauptet. Echte Portal-Auth, Datenzugriff, Menüs, PWA, freier externer KI-Dialog und echter iPhone-TTS-Test bleiben offen. Der alte 25-/45-Testbericht beschreibt historische Snapshots; dies ist der aktuelle Bericht für diesen Schritt.

## Migration / Rollback

Keine DB-Migration und keine neue Abhängigkeit. Ohne gesetzte ADLER_*-Variablen bleibt der Demo-Start mit gültiger INI und Port 5057 kompatibel. Vor späterem autorisiertem Testdeployment Variablennamen/Origin auf Zielhost prüfen. Rollback: Folge-PR nicht übernehmen oder Konfigurationsänderungen auf separatem Branch revertieren; kein Datenrestore nötig. Keine Änderungen an Nginx, systemd oder laufendem Pi in diesem Schritt.

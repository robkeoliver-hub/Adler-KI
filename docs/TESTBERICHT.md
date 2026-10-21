# Prüfbericht – 21.10.2026

## Durchgeführt

- ZIP: 64 Einträge geprüft, alle Textquellen gelesen, SHA-256-Inventar erstellt; Original-App ausschließlich statisch analysiert. Keine Original-App importiert, keine Bestands-DB geöffnet. Endvergleich aller Originaldateien gegen Inventar unverändert.
- Python 3.12/Linux-Cloudumgebung: **25 pytest-Tests bestanden** (letzter Lauf 0,15 Sekunden). API, Anmeldung, Cookie-Schutz, Origin/CSRF, fremde Hosts, gefälschte Cookies, Benutzer-ID-/Rollenmanipulation, verweigerte Rollen, ausschließlich lokale persönliche Werkzeuge, Eingabefehler, Body-/Ratenlimits, Verlaufslimit, Sitzungablauf, Logout, sichere Providerfehler, externer Freigabeschalter, Provider-Payload/Antwortbegrenzung, defekte/zu große Antworten, Timeout und deaktivierte Redirects.
- JavaScript-Syntaxprüfung mit node --check bestanden, Python compileall bestanden.
- Chromium/Playwright bei **375 und 1280 Pixeln**: Anmeldung, lokale Ergebnisfrage, kein horizontaler Überlauf, Sprachfreigabe, simulierte Erkennung und Vorlesen, Stopp, stumme Textantwort nach Sprachfrage, HTML als sicherer Text und Logout bestanden; keine JavaScript-Seitenfehler. Sprachdienste wurden hierfür simuliert, kein tatsächliches Mikrofon/Apple-Dienst benutzt. Screenshots im docs-Verzeichnis visuell geprüft.
- Echter kurzlebiger Waitress-HTTP-Server auf Loopback mit Cookie/CSRF; je zwölf Anfragen, reine synthetische Daten:

| Pfad | Median | p95 (n=12, nächster Rang) | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Mock-Dialog | 0,88 ms | 1,16 ms | 0,73 ms | 1,16 ms |
| Lokale Ergebnisantwort | 0,80 ms | 1,12 ms | 0,73 ms | 1,12 ms |

Das sind HTTP-Rundlaufzeiten in dieser Cloudumgebung, keine Messung auf dem Raspberry Pi 3 und keine Zeit bis zur hörbaren Antwort. Der Browser zeigt seine tatsächliche Request-Zeit. Server-Timing misst zusätzlich Verarbeitung. Netzwerk-KI, Spracherkennung und Sprachausgabe kommen hinzu. Keine Zusage einer hörbaren Antwort innerhalb weniger Sekunden.

## Offen und ausdrücklich nicht behauptet

- Echter iPhone-/iOS-Safari-Test, Mikrofonberechtigung und Siri-Dienst, konkrete deutsche Stimmen und hörbare Latenz. Checkliste in SAFARI.md.
- Desktop-WebKit wurde heruntergeladen, Start jedoch wegen fehlender libgtk-4, libgraphene, libharfbuzz-icu, libmanette, libhyphen und libGLESv2 abgelehnt. Systembibliotheken dieses Hosts wurden dafür nicht verändert. Kein bestandener WebKit-Test behauptet.
- Echte externe KI-Antworten: kein freigegebener Provider und kein API-Schlüssel vorhanden. Adapter mit simuliertem HTTP-Verhalten geprüft, echter Netzwerkbetrieb und Kosten-/Datenschutzbedingungen anbieterabhängig.
- Raspberry-Pi-3-Last, RAM, systemd-Benutzereinheit und HTTPS-Proxy auf Zielhardware. Mit scripts/benchmark.py nach Installation messen; bei Providerwechsel zusätzlich echte freie Dialoge und Sprachlatenz testen. Mock-Benchmark lädt absichtlich nie den echten Provider.
- Produktive Authentifizierung, Rechte und DB-Inhalte nicht ausführbar geprüft, da keine produktive DB/Konfiguration in ZIP. Keine Produktionsintegration vorgenommen.

## Reproduktion

API: `.venv/bin/python -m pytest -q`

HTTP: `.venv/bin/python scripts/benchmark.py` (freier Loopback-Port 5058 erforderlich).

Browser auf separatem Entwicklungsrechner, nicht auf dem Pi:

```sh
.venv/bin/pip install playwright
.venv/bin/python -m playwright install chromium webkit
# Falls nötig OS-Browserbibliotheken auf dem Entwicklungsrechner bereitstellen.
.venv/bin/python tests/browser_smoke.py --engines chromium
.venv/bin/python tests/browser_smoke.py --engines webkit
```

Browser-Smoke routet Requests kontrolliert über den Flask-Testclient. Er prüft UI/Skripte mit strikter CSP, nicht TLS oder ein echtes Safari-Sprachbackend. Der separate Benchmark prüft echte HTTP-Kommunikation.

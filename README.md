# KI-Adler – isolierte Testversion

Eigenständige Flask-App unter `/demo/ki-adler/`, eigener Port 5057. Kein Import der bestehenden Webseite, keine Mitgliederdatenbank, keine Migration, kein Audio-Upload. Mock funktioniert ohne Schlüssel. Echte dialogfähige KI ist über einen optionalen OpenAI-kompatiblen HTTPS-Provider anschließbar; Mock selbst ist ausdrücklich kein Sprachmodell.

## Raspberry Pi 3 installieren

Aktuelles Raspberry Pi OS mit Python 3.11 oder neuer verwenden (auf altem Buster zuerst separat das Betriebssystem planen). Die Schritte verändern keinen laufenden Portalserver. Als normaler Benutzer installieren, niemals in das produktive Portalverzeichnis entpacken.

```sh
sudo apt update
sudo apt install python3-venv unzip
unzip ki-adler-demo.zip -d "$HOME"
cd "$HOME/ki-adler"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/setup.py
```

`config.ini` wird einmalig mit zufälligem Demo-Code und Dateirechten 0600 erzeugt. Dort `demo_code` lokal ablesen und separat an Testende weitergeben. Nicht per URL verschicken oder öffentlich hochladen. Bestehende Konfiguration wird nie überschrieben. `config.example.ini` enthält keine echten Zugangsdaten.

Für einen Vordergrund-Test:

```sh
.venv/bin/python run.py
```

Auf demselben Rechner `http://127.0.0.1:5057/demo/ki-adler/` öffnen. Mit Strg-C beenden. Der Dienst bindet absichtlich nur Loopback. Kein Flask-Debugger. Für einen sicheren Test auf einem anderen Desktop kann ein SSH-Tunnel genutzt werden; die Origin muss dann exakt zur Browseradresse passen. iPhone-Spracherkennung benötigt einen sicheren Kontext.

## Sicher starten und stoppen

Mitgelieferte systemd-Benutzereinheit installieren (erwartet `$HOME/ki-adler`):

```sh
mkdir -p "$HOME/.config/systemd/user"
cp ki-adler-demo.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
./scripts/start.sh
./scripts/stop.sh
```

Kein Autostart wird aktiviert. Optional später bewusst `systemctl --user enable ki-adler-demo.service`; für Start ohne angemeldete Sitzung ist eine separat administrierte Benutzer-Linger-Konfiguration nötig. Kein `killall`, keine PID-Datei, keine Root-Webprozesse. Systemd stoppt nur diesen Dienst. Bei Fehlern `journalctl --user -u ki-adler-demo.service -n 30`; keine Zugangscodes oder Gespräche in Tickets kopieren. Aktuelle Pi-OS-Version vorausgesetzt; systemd-Härtung und MemoryMax auf dem konkreten Pi prüfen. Für andere Installationspfade WorkingDirectory/ExecStart/ReadOnlyPaths anpassen.

## iPhone und HTTPS

Vor dem iPhone-Test einen **separaten** HTTPS-Testhost bzw. separaten Reverse Proxy vor 127.0.0.1:5057 bereitstellen. Dieses Paket installiert oder ändert keinen Webserver, DNS oder Tunnel. Ohne gültiges HTTPS und passenden Host keine verlässliche Browser-Spracherkennung. In `config.ini` etwa `public_origin = https://adler-test.example.org` setzen (eigene echte Adresse), Dienst neu starten. Origin ohne Pfad/Slash, Host-Port exakt passend. Der Proxy muss den Browser-Host erhalten, HTTPS terminieren und ausschließlich diese Demo freigeben; kein Cache und keine Body-/Cookie-/Authorization-Protokollierung. Keine öffentliche Portweiterleitung zu 5057. Keinen vorhandenen Portal-Service-Worker über die Demo legen. Demo-Code ist ein Testzugang, keine Anmeldung an echten Vereinskonten.

Die Seite lädt keine Fremdschriften, Bibliotheken oder Analyseanbieter. Browser-Sprachdienste können jedoch Audio/Text extern verarbeiten; Freigaben in „Sprache & Datenschutz“ beachten. Safari-Fallback und Gerätecheck: [docs/SAFARI.md](docs/SAFARI.md).

## Provider konfigurieren

Standard `provider = mock`: keine externen KI-Aufrufe, simulierte Antworten und lokale Beispieldaten. Kein API-Key nötig. Die vier persönlichen Beispielfragen werden lokal beantwortet.

Für echte Dialoge auf einem **anderen geeigneten Rechner** ein selbst gehostetes Modell mit OpenAI-kompatiblem Chat-Completions-Endpunkt betreiben oder einen nach Datenschutzprüfung geeigneten Anbieter wählen. Der Pi führt kein großes Modell aus. In der privaten config.ini `provider = compatible`, `endpoint` (vollständige HTTPS-URL), `model`, ggf. `api_key` und erst nach Betreiberprüfung `external_approved = true` setzen. TLS-Zertifikate werden geprüft, Weiterleitungen abgelehnt, Netzwerk-Timeout 12 Sekunden je blockierender Operation (keine harte Gesamtfrist bei einem langsam liefernden Server), Ausgabe maximal 160 Tokens angefordert und 1.000 Zeichen übernommen. Schlüssel ausschließlich serverseitig. Ein selbst gehosteter Dienst benötigt passende Hardware; externe Dienste können kostenpflichtig sein. Es werden keine kostenlosen Kontingente vorausgesetzt.

Zusätzlich muss die testende Person den externen **synthetischen** Testdialog in der Oberfläche freigeben. Freitext kann persönliche Angaben enthalten: deshalb keine echten Namen, Kinderdaten oder Gesprächsinhalte aus dem Produktivportal eingeben. Diese Demo ist nicht für extern verarbeitete echte Kinderdaten freigegeben. Eine künftige Integration benötigt die gesonderte Datenschutzentscheidung im Integrationsplan. Der Provider erhält nur begrenzten Demo-Verlauf, nie eine Datenbankverbindung oder SQL-Werkzeuge.

## Datenschutz und Grenzen

Sitzungen liegen nur im Prozess-RAM, haben eine feste Lebenszeit von 15 Minuten und werden spätestens 30 Sekunden danach durch einen schlafenden Aufräum-Thread entfernt; bei Requests sofort. Maximal 128 Sitzungen, acht Verlaufseinträge je Sitzung; UI zeigt maximal 20 Nachrichten. Nach Beenden oder Dienstneustart gelöscht. Bei Seitenwechsel wird Logout versucht; bei Netzverlust greift der Ablauf. Keine Browser-Speicher-API oder dauerhafte Gesprächsspeicherung, keine Audiodateien. Betriebssystem-Swap/Core-Dumps und vorgelagerte Logs müssen Betreiber bei realem Einsatz ebenfalls datenschutzgerecht konfigurieren. Browser-/Apple-Dienste haben eigene Regeln.

Maximal 600 Eingabezeichen, 8 KiB HTTP-Body, zehn Chats/Minute/Sitzung und global 30 Chats/Minute. Login fünf/Minute je direkter IP sowie global 60; hinter lokalem Proxy teilen sich Tester bewusst das IP-Limit. Kein Vertrauen in frei übergebene Forwarded-For-Header. Zwei parallele KI-Aufrufe, vier Waitress-Threads, nur lesende synthetische Werkzeuge. Kein Betreuerzugriff freigeschaltet. Keine echte Datenbank angebunden. Fehlerantworten verraten keine Prompts, Schlüssel oder Provider-Fehlertexte.

## Tests

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/benchmark.py
```

Benchmark nutzt echte lokale HTTP-Aufrufe gegen einen kurzlebigen separaten Waitress-Server, keine Produktivdaten. Browser-Test benötigt zusätzlich Playwright und installierte Browser; siehe tests/browser_smoke.py. Ergebnisse und offene Prüfungen stehen in docs/TESTBERICHT.md. Keine garantierte Pi-/Sprachlatenz.

Analyse vor Änderungen: [docs/ANALYSE.md](docs/ANALYSE.md), vollständige Routen/Modelle: [docs/INVENTAR.md](docs/INVENTAR.md), Integration erst nach Freigabe: [docs/INTEGRATIONSPLAN.md](docs/INTEGRATIONSPLAN.md).

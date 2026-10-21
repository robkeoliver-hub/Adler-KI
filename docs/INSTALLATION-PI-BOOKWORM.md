# KI-Adler auf Debian Bookworm installieren

## Geprüfter Umfang

Das Skript installiert vorhandenen Code aus PR #4, Commit
`8a6913eb8f666eb00c0d31c171dd50179884b49d`. Dieser enthält PR #1–#3.
Die PRs sind noch nicht zusammengeführt; `main` enthält lediglich die Start-README.
Es werden weder eine neue Vereinsverwaltung noch Datenbankmigrationen ausgeführt.

**Die Anwendung bleibt eine gekennzeichnete Mock-Demo mit Beispieldaten.**
Echte Mitgliederdaten, gemeinsamer Portal-Login und ein externer LLM sind nicht angebunden.
Der produktive Modus verweigert ohne geprüfte Adapter weiterhin den Start.
Die einklappbare Gesprächsansicht aus PR #4 wird installiert; das bestehende Portal
bekommt dadurch noch keinen eingebetteten Assistenten. Dafür fehlen der abschließend
geprüfte aktuelle Portalexport sowie die Prüfung von Authentifizierung und Rollen.
Den bisher unvollständig geprüften Export nicht in das öffentliche Repository laden.

## Voraussetzungen

Auf dem Pi als Benutzer `pi` ausführen, nicht `sudo python3`.
Erwartet werden Bookworm, Python 3 mit venv, curl, iproute2 (`ss`), systemd und
Internetzugriff auf GitHub/PyPI. Es erfolgen keine Betriebssystemupdates.
Die alte Installation muss aus `~/ki-adler-test/.venv/bin/python run.py`
auf 127.0.0.1:5057 laufen. Ihre PID wird aktuell ermittelt, niemals aus alten Angaben übernommen.
Ein bereits durch einen systemd-Dienst verwalteter Altprozess führt zum sicheren Abbruch,
weil dessen Start-/Stoppverfahren zuerst geprüft werden muss.
Die bestehende Konfiguration wird aus `config.ini` und dem Prozessumfeld gelesen;
bei abweichendem Dateinamen `--config /absoluter/pfad.ini` angeben.
Niemals Passwörter oder Konfigurationsinhalte in einen Chat kopieren.

## 1. Herunterladen und getrennt installieren

Diese Befehle gehören in das Terminal des Raspberry Pi, nicht in Safari oder GitHub:

```bash
curl -fL https://raw.githubusercontent.com/robkeoliver-hub/Adler-KI/ki-adler/pi-installation/scripts/install_pi.py -o /home/pi/install_ki_adler.py
python3 /home/pi/install_ki_adler.py
```

Das Skript prüft das Quellarchiv gegen einen fest eingebauten Manifest-Hash und
alle Datei-Hashes. Es sichert alten Code und effektive Konfiguration in einem privaten
Archiv unter `~/ki-adler/backups/`. Die alte virtuelle Umgebung bleibt unverändert;
das Archiv ist kein vollständiges Betriebssystem-Backup.
Anschließend installiert es separat unter `~/ki-adler/releases/`, führt die 76 Tests
der Anwendung aus und startet `ki-adler-next.service` auf **127.0.0.1:5059**.
API-Tests benutzen einen neu erzeugten synthetischen Demo-Zugang.
Der alte Dienst auf 5057 läuft währenddessen weiter. `sudo` wird nur lokal für den
neuen systemd-Dienst benötigt; ein eventuell abgefragtes Passwort bleibt am Pi.

`~/ki-adler/private/` enthält geschützte Konfiguration, Wiederherstellungsinformationen
und Protokolle. Dort können Zugangsdaten und Prozessvariablen enthalten sein:
nicht hochladen oder öffentlich teilen. Ordner sind 0700, private Dateien 0600.
Ein erneut aufgerufenes Skript prüft eine vollständige Installation und legt keine
zweite an. Nach einem unvollständigen Abbruch werden vorhandene Releases/Dienste
nicht blind überschrieben. Dann die genaue Fehlermeldung ohne private Dateien prüfen.

## 2. Nach erfolgreichen Tests den KI-Endpunkt umstellen

```bash
python3 /home/pi/install_ki_adler.py --activate
```

Erst nach bestandenen Tests wird ausschließlich der überprüfte alte KI-Prozess
geordnet beendet. Der neue Dienst übernimmt 5057. Die öffentliche Adresse bleibt:

https://adlerzug.duckdns.org/demo/ki-adler/

Nginx, Port 5000 und `~/schuetzenjugend` werden nicht verändert.
Die öffentliche Erreichbarkeit wird vor und nach der Umschaltung ohne Login geprüft.
Bei einem Start-/Erreichbarkeitsfehler versucht das Skript, den bisherigen Prozess mit
seinem ursprünglichen Arbeitsverzeichnis und Prozessumfeld wiederherzustellen.
Kein `killall`, kein SIGKILL, keine Abschaltung fremder Prozesse.

**Autostart beim Booten wird noch nicht aktiviert.** Die bisherigen Boot-Startmechanismen
sind unbekannt und müssen vor `systemctl enable` geprüft werden, damit nicht zwei
Prozesse denselben Port beanspruchen. Bis dahin den Pi nicht für diesen Zweck neu starten.

## 3. Rückkehr und Diagnose

```bash
python3 /home/pi/install_ki_adler.py --rollback
systemctl status ki-adler-next.service --no-pager
```

Rollback stoppt den neuen KI-Dienst, startet die unveränderte Altinstallation auf 5057
und den Kandidaten getrennt auf 5059. Es benötigt den weiterhin vorhandenen alten
Quellcode samt virtueller Umgebung. Ein belegter Port oder unerwarteter Prozess führt
zum Abbruch statt zur erzwungenen Abschaltung. Es gibt keine Portal-/DB-Migration.
Die Wiederherstellung wurde simuliert getestet, nicht auf diesem konkreten Pi.

## Prüfbericht und verbleibende Abnahme

In der Cloud bestanden **98 Tests** (Python 3.12): 76 Anwendungstests und 22
Installertests. Geprüft wurden unter anderem Archivmanipulationen, private Backups,
Konfigurationsübernahme, Port-/Prozessprüfung, Idempotenz, fehlgeschlagene Aktivierung,
Rückkehr zur Altversion und echte lokale Waitress-HTTP-Anfragen mit Secure-Cookies,
CSRF, synthetischem Login/Chat und Logout. Das tatsächliche gepinnte GitHub-Archiv
wurde ebenfalls gegen das Manifest geprüft. Auf dem Pi werden die 76 Tests der
unveränderten Anwendung erneut ausgeführt; Bookworm/Python 3.11/systemd und echte
Pi-Laufzeiten sind hier nicht praktisch nachgewiesen. Kein direkter SSH-Zugriff lag vor.

Nach Umschaltung am iPhone prüfen: bestehende Portalmenüs und Anmeldung, Demo öffnen,
Begleiter ein-/ausblenden, Textfrage (keine automatische Sprachausgabe), Mikrofontaste,
Berechtigungsverweigerung, deutsche Ausgabe und Stopptaste. Sprachfunktionen hängen
von iOS-Version und verfügbaren Systemstimmen ab; keine Autoplay-Garantie.
Ergänzend gilt `docs/SAFARI.md`. Keine Tests mit echten Kinder- oder Mitgliederdaten.

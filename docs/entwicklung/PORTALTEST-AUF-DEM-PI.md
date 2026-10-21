# Getrennter Test des vorhandenen Portals mit KI-Adler

## Was dieser Schritt leistet

Das Skript `scripts/prepare_portal_test.py` verwendet den privat bereitgestellten,
für diesen begrenzten Test lokal geprüften Portalexport (SHA256
536a6a72407b8f6a370e8f294f88d78b0c51de9cdc6e007dcbcedc237f298770) und den festen
Stand von PR #7, Commit f583caa88b14a1e7238b2d06b0bf0d8d747c0d0a.
Es erstellt keine neue Vereinsverwaltung, sondern kopiert die vorhandene Anwendung
in einen neuen privaten Testordner und hängt den vorhandenen neuen Adapter ein.
Das ist keine Freigabe zur öffentlichen Veröffentlichung des Exports.
Der Export selbst wird nicht veröffentlicht. Veränderte Exporte werden abgewiesen.

Es wird nur `~/ki-adler-portaltest` neu angelegt. Das Skript liest weder die echte
Datenbank noch die echte Portal-Konfiguration oder deren virtuelle Umgebung.
`~/schuetzenjugend`, `~/ki-adler-test` und `~/ki-adler` werden nicht geändert.
Keine Dienst-/Proxyänderung, kein sudo, kein systemd, kein apt, keine Produktivmigration.
Port 5000, 5057 und 5059 bleiben erhalten. Kein bestehender Ordner wird überschrieben.
Eine vorhandene unvollständige Kopie führt zu Abbruch statt zu automatischer Löschung.

## Durchführung auf dem Pi

Als Benutzer **pi**, nicht `sudo python3`, im bisherigen Terminal ausführen:

```bash
curl -fL https://raw.githubusercontent.com/robkeoliver-hub/Adler-KI/ki-adler/portaltest-installation/scripts/prepare_portal_test.py -o /home/pi/prepare_portal_test.py
python3 /home/pi/prepare_portal_test.py
```

Voraussetzungen: Bookworm, Python 3 mit venv, ausreichend freier Speicher für eine
zusätzliche virtuelle Umgebung und Zugriff auf GitHub/PyPI. Kein Tesseract-Systempaket
wird installiert: OCR-Aufrufe sind in diesem Test nicht freigegeben. Getestet wurde
hier Python 3.12/x86_64; der echte Pi mit Python 3.11/ARM64 bleibt separat abzunehmen.
Installation kann auf dem Pi einige Minuten dauern. Keine Laufzeitgarantie.

Das Skript führt nacheinander aus:

1. Prüft exakten Export-Hash, ZIP-Pfade, Limits, Links und Laufzeitdateien.
2. Lädt den festgelegten KI-Code per TLS, prüft unabhängig gepinntes Manifest und
   sämtliche Dateihashes. Ein späterer Branchstand wird nicht automatisch übernommen.
3. Erstellt eine neue private Kopie, neue venv und neue zufällige Testschlüssel.
4. Ergänzt dort Panelaufruf, deutlichen Testbanner und deaktiviert ausschließlich
   in der Kopie die Registrierung des Root-Service-Workers.
5. Importiert erst jetzt die **Kopie** von app.py. Deren vorhandene create_all-/
   Schema-/Abzeichenseeds dürfen ausschließlich die neue Testdatenbank bearbeiten.
6. Legt zwei künstliche Testkinder, verschiedene Testresultate und einen als TEST
   markierten Kalendertermin an. Keine Daten aus echten Konten werden übernommen.
7. Prüft fünf bestehende Jugendseiten pro Testkind sowie Loginbindung, Datenisolation,
   eigene Ergebnisse, Kalender, Fremd-ID-Ablehnung, Widerruf und Schreibsperre.
8. Startet bei Erfolg einen eigenen Hintergrundprozess auf **127.0.0.1:5071**.
   Belegter Port führt zu Abbruch; kein fremder Dienst wird beendet.

Erfolgsanzeige: `Portal-Kopie ... Portaltests bestanden` und anschließend
`Portaltest läuft getrennt auf 127.0.0.1:5071`. Die private setup.log enthält eine
Zusammenfassung mit `ok: true`, `checks: 23`, `synthetic_only: true`.
Bei Fehlern wird nicht automatisch erneut installiert. Logs nicht ungeprüft teilen.

## Start, Status und Rücknahme

```bash
python3 /home/pi/prepare_portal_test.py --status
python3 /home/pi/prepare_portal_test.py --stop
python3 /home/pi/prepare_portal_test.py --start
```

Start prüft die vorbereiteten Codehashes und legt keine zweite Instanz an.
Stopp prüft PID, Startzeit, Benutzer, Arbeitsverzeichnis und genaue Argumente und
verwendet Linux-pidfd. Keine PID aus alten Screenshots, kein killall, kein SIGKILL.
Die Listener-Zuordnung wird beim Start über /proc gegen den eigenen Prozess geprüft.
Rücknahme ist ausschließlich `--stop`; alle bestehenden Dienste laufen unabhängig.
Keine Datenmigration zurückzunehmen, keine Dateien automatisch löschen.
Kein Autostart nach Neustart; dieser kurzlebige Test ist kein Produktivdienst.

## Sicherheit und Grenzen

Private Ordner sind 0700, Konfigurations-/Protokolldateien 0600. Die Testkonfiguration
unter private/config.json enthält nur neu erzeugte Testwerte. private/access.json
enthält die Pfade der zwei künstlichen QR-Konten, keine echten Jugendtokens.
Der Testprozess löscht vor dem App-Import geerbte Umgebungsvariablen und setzt
seine eigenen Testwerte. Das ist logische Trennung durch Pfade/DB/Prozess und
keine Betriebssystem-Sandbox: Beide laufen weiterhin als derselbe Benutzer pi.
Keine echten Personen/Fotos in den Test eingeben. Sämtliche vorhandenen POST-
Schreibfunktionen einschließlich Betreuerlogin sind gesperrt, ausgenommen die drei
neuen KI-Session-/Lese-Endpunkte. Navigation und Jugendseiten bleiben zum Testen da.
Keine Provideranbindung, kein externer LLM, keine offiziellen Vergaben über KI.

## iPhone-Test ist der folgende Schritt

127.0.0.1:5071 ist absichtlich **nicht öffentlich**. Es gibt dadurch noch keinen
funktionierenden iPhone-Link. Flask-Secure-Cookies und Speech-Funktionen benötigen
für den End-to-End-Test eine korrekt eingerichtete HTTPS-Testadresse. Ein bloßes
HTTP-Portforwarding liefert keine vollständige Sprach-/Login-Abnahme.

Vor einer öffentlichen Testweiterleitung müssen die tatsächliche Nginx-/Tunnel-
Konfiguration, TLS und gewünschter Host/Mountpfad geprüft werden. Keine Vermutung
über die effektive Proxykette. Anschließend separate Freigabe einer konkreten,
reviewbaren Proxyänderung einholen, sichere Testadresse und danach iPhone-Abnahme.
Der Adapter aus PR #7 erwartet derzeit einen Root-Mount der Jugendpfade; ihn nicht
ungeprüft unter einen URL-Präfix hängen. Noch keinen Routerport öffnen und die
bestehende KI-Weiterleitung auf 5057 nicht ersetzen.

## Tatsächliche Nachweise

- 143 pytest-Tests bestanden: 125 bisherige und 18 neue Aufbau-/Archiv-/Stopp-Tests.
- Zusätzlich kompletter realer Cloud-Aufbau mit dem privat hochgeladenen Export
  und dem echten gepinnten GitHub-Archiv: neue venv, Portalimport ausschließlich in
  neue Kopie, 23 integrierte Prüfungen mit tatsächlichen Jugendtemplates/API.
- Tatsächlicher Waitress-Start auf Loopback, wiederholter Start ohne Doppelinstanz,
  kontrollierter Stopp, Neustart und erneuter Stopp bestanden.
- Testdienst nach Prüfung wieder angehalten. Kein Raspberry-Pi-Zugriff, keine
  Behauptung einer Pi-/iPhone-/OCR-/Betreuerabnahme.

Dieser PR baut auf PR #7 auf; nichts wird automatisch gemergt oder installiert.

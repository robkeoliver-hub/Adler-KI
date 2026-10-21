# Bestehenden Portaltest für den HTTPS-Präfix vorbereiten

## Ziel

Der Betreiber hat den Portaltest auf 5071 und die erfolgreiche private Nginx-
Vorschau bestätigt. Es fehlt die Umstellung der bestehenden **Testkopie** auf
/demo/ki-adler-portaltest und einen eigenen Cookie-Namen. Das Skript
scripts/update_test_mount.py erledigt nur diesen Schritt. Keine Nginx-Datei wird
geöffnet oder geändert, kein Reload durchgeführt. Noch kein öffentlicher Testlink.

## Durchführung auf dem Pi

Als pi, ohne sudo vor python3:

```bash
curl -fL https://raw.githubusercontent.com/robkeoliver-hub/Adler-KI/ki-adler/testmount-update/scripts/update_test_mount.py -o /home/pi/update_test_mount.py
python3 /home/pi/update_test_mount.py
```

Es wird der feste geprüfte Stand 1b25ed14325cf72906a4bfadfcd71ec56936673f geladen.
Unabhängiger Manifest-Hash und alle Quelldateihashes müssen passen. Die bestehende
Installationssteuerung prepare_portal_test.py muss dem bekannten Code entsprechen;
veränderte Steuerdateien werden nicht importiert. Paketinstallation, neue venv,
neuer Portalexport und neue Datenbank sind nicht nötig.

Das Skript:

1. Prüft die vorhandene Testkopie und ihre Codehashes, den ursprünglichen Runner
   und die beiden bekannten alten Paneldateien; bei Abweichung Abbruch.
2. Stoppt ausschließlich den identifizierten Testprozess auf 5071 über die
   vorhandene PID-/Startzeit-/CWD-/Argument-/pidfd-Prüfung.
3. Sichert Runner, zwei Paneldateien, Codehashes, Zugriffspfade sowie einen
   konsistenten SQLite-Backupstand der künstlichen Testdaten. Die neue Mountdatei
   war vorher nicht vorhanden und wird bei Rücknahme entsprechend entfernt.
4. Übernimmt die geprüften Präfixdateien und ergänzt den Test-Runner um den
   explizit isolierten WSGI-Mount. Cookie heißt ki_adler_portaltest_session und
   ist auf den Testpfad beschränkt. Root-Portal-Session bleibt unverändert.
5. Prüft tatsächliche Portalvorlagen/API unter dem Präfix: 27 Checks, darunter
   beide Testkonten getrennt, fünf Jugendseiten, eigene Ergebnisse, CSRF-Bindung,
   Jugendkalender, Fremd-ID-Ablehnung, Widerruf und unverändertes Produktionscookie.
   Ein inzwischen abgelaufener künstlicher Termin darf korrekt fehlen.
6. Startet den Testprozess wieder auf 5071. Bei Fehlern nach vollständiger Sicherung
   werden vorheriger Code, Datenbank und Zugriffspfade zurückgenommen und die
   bisherige Testkopie gestartet. Keine Produktivdienste werden gestoppt.

Erfolgsanzeige:
`Testkopie erfolgreich für HTTPS-Pfad und eigenes Cookie vorbereitet.`
`Nginx unverändert: Der öffentliche Testlink ist noch NICHT aktiviert.`

Ein erneuter Aufruf prüft die bereits umgestellte Kopie und legt keine zweite
Installation oder Sicherung an. Es wird nichts ungefragt überschrieben. Bei
unvollständigen früheren Versuchen sicher anhalten statt Sicherungen löschen.

## Sicherung und Rücknahme

Alle Dateien unter ~/ki-adler-portaltest/private/ bleiben privat (0600/0700):
https-backup-v1 enthält ursprüngliche Testdateien, Manifest und synthetische DB;
https-update.json dokumentiert Updatezustand und Quellcommit. mount-source.zip
enthält den geprüften öffentlichen Code und ermöglicht Offline-Rücknahme.
Keine dieser Dateien ungeprüft teilen. Bereits vorhandene Testschlüssel und
synthetische QR-Tokens bleiben unverändert; Zugriffspfade erhalten nur den Präfix.

```bash
python3 /home/pi/update_test_mount.py --rollback
```

Die Rücknahme nutzt den geprüften lokalen Quellcache, benötigt keine Netzwerk-
verbindung und prüft zuerst Sicherungsdateien/Hashes. Sie funktioniert auch ohne
erfolgreiche Validierung der neuen Testdateien. Unbekannte Prozesse, beschädigte
Sicherungen und fremd veränderte neue Dateien führen zum Abbruch statt Löschung.

Die bisherige Steuerung prepare_portal_test.py --start/--stop bleibt verwendbar;
der lokale Root-Healthcheck enthält weiter den synthetischen Testbanner. Kein
Autostart wird eingerichtet. Eine spätere Nginx-Aktivierung muss separat zurück-
genommen werden; dieses Skript ändert auch bei --rollback keine Proxyregeln.

## Tatsächliche Tests

171 pytest-Tests bestanden: 161 bestehende plus 10 neue Update-/Rücknahmetests.
Zusätzlich tatsächlicher Ablauf mit dem privaten Portalexport in einer Cloud-
Testkopie und realem gepinntem GitHub-Archiv: Update, 27 integrierte Checks,
wiederholtes Update ohne Doppelinstanz und Rücknahme bestanden. Ein absichtlich
fehlgeschlagener neuer Selbsttest hat die vorherige Testkopie automatisch
wiederhergestellt und gestartet. Anschließend Cloud-Testdienst angehalten.
Keine Behauptung einer bereits erfolgten Pi-/iPhone-/HTTPS-Abnahme.

## Noch vor öffentlichem Test nötig

Nach bestätigtem Pi-Update: tatsächlichen Nginx-Kandidaten prüfen, konkrete
Aktivierung mit Originalbackup/Hashschutz und nginx -t vorbereiten und dafür
Betreiberfreigabe einholen. Erst danach kontrollierter Reload und HTTPS/iPhone-
Probe. Das produktive Portal auf 5000, die Demo auf 5057 und Drucker/Webcams bleiben
unberührt. Diese Freigabe wird durch das Testkopie-Update nicht vorweggenommen.

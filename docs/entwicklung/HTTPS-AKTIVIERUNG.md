# Letzte HTTPS-Prüfung und gesonderte Aktivierung

## Aktueller Nachweis

Der Betreiber bestätigt am 21.10.2026 den erfolgreichen Mount-Update auf dem Pi,
die integrierten Tests und unveränderten Nginx-Zustand. Das Skript
activate_test_proxy.py trennt die letzte Prüfung vollständig von der Aktivierung.

## Jetzt ausschließlich prüfen

Im Pi-Terminal:

```bash
curl -fL https://raw.githubusercontent.com/robkeoliver-hub/Adler-KI/ki-adler/https-aktivierung/scripts/activate_test_proxy.py -o /home/pi/activate_test_proxy.py
sudo python3 /home/pi/activate_test_proxy.py --check
```

Root ist hier zum Lesen der root-only Site und TLS-Schlüssel durch nginx -t nötig.
Es werden weder Dateirechte gelockert noch bestehende Dienste gestoppt. Der geprüfte
Vorschauhelfer /home/pi/preview_test_proxy.py muss exakt dem bekannten Stand
entsprechen (Dateihash wird vor einem Import geprüft).

--check liest die wirksame Konfiguration mit nginx -T, bestätigt Zielserver und
bestehende Weiterleitungen, prüft den lokalen Testmount auf 5071 und die beiden
künstlichen Zugriffspfade. Alle geladenen Konfigurationsdateien werden privat in
ein temporäres Verzeichnis kopiert. Includes zeigen in dieser Kopie auf die
entsprechenden Kopien; nur die vorgesehene Site erhält den zusätzlichen Testblock.
Andere Server einschließlich Drucker/Webcams bleiben inhaltlich erhalten.

Die Kopie wird mit echtem `nginx -t -c <private-Kopie>` geprüft. Keine Start-/Reload-
Anweisung, keine Änderung einer aktiven Nginx-Datei. Temporäre Kopien werden entfernt.
Nginx behält seinen normalen kompilierten Prefix für Module/Logs; relative oder
dynamische TLS-/Auth-Dateipfade führen vorsichtshalber zum Abbruch. Der Include-
Abgleich behandelt * nur innerhalb eines Pfadsegments, keine rekursiven Globs.

Unter /var/lib/ki-adler-test-proxy entsteht ein root-eigener privater Zustandsordner
(0700, Dateien 0600) mit geprüfter Vorschau und Vorschlags-Hashes. Fehlerdetails
bleiben in last-error.log und dürfen nicht ungeprüft geteilt werden. stdout enthält
nur statische Statusmeldungen. Das ist kein öffentlicher Datenendpunkt.

Erfolgsanzeige:
`NGINX-KANDIDAT GEPRÜFT: nginx -t mit privater Kopie erfolgreich.`
`NICHT aktiviert. Vor --apply ist die ausdrückliche Freigabe erforderlich.`

## Erst nach ausdrücklicher Freigabe

Der folgende Befehl darf erst nach erfolgreichem --check und Betreiberfreigabe
für den konkreten zusätzlichen HTTPS-Testpfad ausgeführt werden:

```bash
sudo python3 /home/pi/activate_test_proxy.py --apply
```

Er bestätigt alle Konfigurationshashes erneut, wiederholt die Prüfung der Kopie,
prüft vorher öffentliches Portal und bisherige Demo, sichert die aktuelle originale
Site root-only und ergänzt atomar ausschließlich den geplanten Block. Eigentümer,
Gruppe und Dateimodus der Site bleiben erhalten; ein sites-enabled-Symlink wird
nicht ersetzt. Anschließend nginx -t auf der tatsächlichen Konfiguration und
`systemctl reload nginx`. Kein Neustart von Portal, Demo oder Test-Backend.

Nach Reload folgen HTTPS-GET-Prüfungen mit gültiger Zertifikatsprüfung auf Testpfad,
Portal und Demo, ohne Mitgliedertokens oder Zugangsdaten an Netzwerktests zu hängen.
Bei Fehlern wird die gesicherte Originalsite atomar wiederhergestellt, erneut
geprüft und geladen. Bei fremden Inhaltsänderungen wird keine erzwungene Rücknahme
vorgenommen. Ein fehlgeschlagener Rückweg wird ausdrücklich als unbestätigt gemeldet.

Nur nach erfolgreicher Aktivierung werden die zwei Links der **künstlichen**
Testkonten angezeigt. Keine realen Jugendkonten werden gelesen oder ausgegeben.
Nginx-Accesslog ist ausschließlich für den neuen Testpfad aus, damit Tokenpfade
nicht dort gespeichert werden. Keine Änderung an globalen Log-/Proxyregeln.

## Rücknahme

```bash
sudo python3 /home/pi/activate_test_proxy.py --rollback
```

Root-only Sicherung und aktuelle Site werden vor Rücknahme per Hash geprüft.
Der Vorgang unterstützt auch einen unterbrochenen, als pending dokumentierten
Aktivierungsversuch. Bestehende fremde Änderungen oder defekte Sicherung: Abbruch,
kein Überschreiben. Die Portal-Testkopie auf 5071 bleibt separat bestehen; deren
Code-Rücknahme ist unabhängig und ersetzt diese Proxy-Rücknahme nicht.

## Grenzen und Tests

187 pytest-Tests bestanden (171 bestehende plus 16 neue). Neue Tests prüfen nur
synthetische Dateien und simulierte nginx-/systemctl-/HTTPS-Ergebnisse: Check ohne
Aktivierung, Schutz vor veränderten Konfigurationen, Include-Kopie mit unverändertem
Druckerserver, erfolgreiche Aktivierung/Rücknahme, Fehler bei Syntax/Reload/HTTPS,
unterbrochene Aktivierung, fehlende Testzugriffspfade und fremde Änderungen.
Kein echter nginx-Dienst war in der Cloud vorhanden. Deshalb ist das reale --check
auf dem Pi eine zwingende noch offene Abnahme, keine bereits erledigte Prüfung.

Keine Aktivierung auf dem Pi durch Codex, keine neue Freigabe angenommen. iPhone-
Sprachausgabe und die gesamte Bedienung werden nach genehmigter Aktivierung geprüft.
Die Anwendung bleibt bei den zwei festen Lesewerkzeugen; kein freier LLM.

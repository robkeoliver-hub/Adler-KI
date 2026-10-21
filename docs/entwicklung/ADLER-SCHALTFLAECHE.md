# Darstellungsfehler: Adler hinter der unteren Navigation

Nach bestätigter HTTPS-Aktivierung meldete der Betreiber die fehlende Adler-
Schaltfläche. Direkte GET-Prüfung: Panel im HTML vorhanden, CSS/JS jeweils 200.
Die echte Portal-CSS setzt die feste Jugendnavigation auf z-index 1000, während
unser Panel z-index 900 hatte und direkt am unteren Rand lag. Die Navigation
verdeckte den Launcher. Die bisherige synthetische Hostnavigation war nicht fest
positioniert und hat diesen Fehler daher nicht abgedeckt.

## Korrektur

Der Abstand zum unteren Rand steigt ausschließlich für #portal-adler von 12 auf
100 Pixel plus iPhone-Safe-Area. Der Adler liegt damit oberhalb der tatsächlichen
Menüleiste; diese behält ihre Position und ihren höheren Stapelrang. Keine Änderung
an Portalnavigation, Datenbank, API, Authentifizierung oder Nginx.

## Vorhandene Pi-Testkopie reparieren

Als pi ohne sudo ausführen:

```bash
curl -fL https://raw.githubusercontent.com/robkeoliver-hub/Adler-KI/ki-adler/adler-button-sichtbar/scripts/fix_adler_button.py -o /home/pi/fix_adler_button.py
python3 /home/pi/fix_adler_button.py
```

Das Standardbibliothek-Skript prüft die genaue bisherige CSS-Prüfsumme und den
vorhandenen Codehash-Eintrag, sichert beide privat und aktualisiert genau diese
CSS-Datei sowie ihren Eintrag. Keine Paketinstallation, kein Prozessstopp und
kein Reload. Wiederholter Aufruf ist ohne zweite Sicherung möglich. Unbekannter
Dateistand wird nicht überschrieben. Schreibfehler während der Übernahme nehmen
beide Änderungen zurück. Vorhandene andere Codehashes bleiben erhalten.

Danach dieselbe Testseite in Safari **neu laden**. Die Mount-Antworten sind no-store.
Die grüne Schaltfläche „🦅 KI-Adler“ soll nun rechts oberhalb der unteren Navigation
erscheinen. Es ist zunächst der vorhandene Launcher, noch keine fertige animierte
Adlerfigur. Nicht mit dem separaten Demo-Pfad /demo/ki-adler/ verwechseln.

Private Sicherung unter ki-adler-portaltest/private/adler-button-css-backup-v1.
Rücknahme bei Bedarf:

```bash
python3 /home/pi/fix_adler_button.py --rollback
```

Wenn zwischenzeitlich andere Codehashes aktualisiert wurden, verweigert das Skript
deren Überschreiben bei Rücknahme. Produktivportal 5000 und bisherige Demo 5057
werden zu keinem Zeitpunkt berührt.

## Nachweise

191 pytest-Tests bestanden (187 bisherige plus 4 für Korrektur, Wiederholung,
Schreibfehler/Rücknahme und Schutz vor späteren Änderungen).
Der Browser-Smoke verwendet jetzt eine feste untere Hostnavigation mit höherem
z-index und prüft den tatsächlichen Klicktreffer und Abstand zum Menü, zusätzlich
zu Root-/Präfixansicht, Texteingabe und Schließen.

Zusätzlich wurden echte HTML-/CSS-/JS-Antworten der öffentlichen synthetischen
Testseite im Chromium-Browser geprüft. Ohne CSS-Korrektur lag elementFromPoint am
Buttonmittelpunkt auf der Navigation; nach ausschließlich lokalem Überschreiben
der CSS-Antwort war der Button erreichbar. Bei 375 Pixeln: Buttonunterkante 797,
Navigationsoberkante 831; bei 1280: 797 und 827 (900 Pixel Ansichthöhe).
Öffnen/Schließen bestanden. Die Live-Antworten wurden dabei nicht auf dem Pi
verändert. Echte Safari-/Touch-Abnahme nach Pi-Korrektur bleibt offen.

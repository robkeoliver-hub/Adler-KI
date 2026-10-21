# HTTPS-Portaltest: Pfad und sichere Vorschau

## Beobachtete Infrastruktur

Der Betreiber hat die gefilterte Ausgabe von nginx -T bereitgestellt:
HTTPS für adlerzug.duckdns.org, location ^~ /demo/ki-adler/ auf 5057 und location /
auf 5000. Zusätzlich läuft ein separater Standardserver für Drucker/Webcams.
Dessen Konfiguration wird nicht bearbeitet. Datei, vollständige Direktiven und
exakte proxy_pass-Werte sind aus dem Screenshot noch nicht sicher bekannt.
Deshalb kein automatisches Patchen oder Reload anhand des Screenshots.

Der Portaltest auf 127.0.0.1:5071 ist laut Terminalausgabe auf dem Pi erfolgreich
aufgebaut. Die bestehende Testkopie ist noch nicht unter einem URL-Präfix montiert.
Ein bloßes Hinzufügen einer Nginx-Regel würde deshalb noch keinen korrekten Test
liefern. Es erfolgen in diesem PR keine automatischen Änderungen an dieser Kopie.

## Konkret vorgesehene Ergänzung

```nginx
location = /demo/ki-adler-portaltest {
    return 308 /demo/ki-adler-portaltest/;
}
location ^~ /demo/ki-adler-portaltest/ {
    proxy_pass http://127.0.0.1:5071;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_no_cache 1;
    proxy_cache_bypass 1;
    access_log off;
}
```

proxy_pass hat absichtlich keinen abschließenden Slash: Der Testprozess soll den
vollständigen Präfix erhalten und über DispatcherMiddleware selbst zuordnen.
Bestehende Locations, TLS, Sicherheitsheader, Dienste und Router bleiben erhalten.
Neue Location deaktiviert Tokenpfad-Protokollierung im Nginx-Accesslog. Keine
Änderung an globalen Logregeln oder am Root-Service-Worker. Die vorbereitete
Testmount-Erweiterung setzt no-store/no-referrer auf allen Testantworten.

## Jetzt ausführbar: ausschließlich eine private Vorschau erstellen

Als pi im Terminal:

```bash
curl -fL https://raw.githubusercontent.com/robkeoliver-hub/Adler-KI/ki-adler/test-https-vorschau/scripts/preview_test_proxy.py -o /home/pi/preview_test_proxy.py
sudo nginx -T 2>/dev/null | python3 /home/pi/preview_test_proxy.py
```

sudo gilt hier ausschließlich dem lesenden nginx -T. Der Pythonprozess läuft als
pi und benötigt keine Rootrechte. Er schreibt nur in
~/ki-adler-portaltest/private/proxy-preview/:

- original.conf: unveränderte aktuelle Site als private Wiederherstellungsgrundlage;
- candidate.conf: private Vorschau mit genau dem zusätzlichen Block;
- report.json: Zielpfad und Prüfsummen, applied=false.

Alle Dateien 0600, Ordner 0700. Sie können vertrauliche vorhandene Konfigurationswerte
enthalten und dürfen weder hochgeladen noch auf GitHub veröffentlicht werden.
Nur die statische Abschlussmeldung ist zum Teilen gedacht. Kein vollständiger
nginx-Dump wird ausgegeben oder dauerhaft gespeichert.

Der konservative Parser beachtet Kommentare und Anführungszeichen, sucht genau
einen SSL-Server auf 443 mit dem bekannten Namen und bestätigt die beiden
bestehenden Weiterleitungen. Mehrdeutige Zielserver, abweichende Zielports,
Server-Includes und bereits vorhandene Testregeln führen zum Abbruch statt zu
Vermutungen. Aktueller Dateiinhalt und nginx-Dump müssen zusammenpassen. Es wird
keine aktive Datei überschrieben, kein nginx -t gestartet und kein Reload ausgeführt.
Der Parser ersetzt nicht die spätere echte nginx-Syntaxprüfung.

## Vorbereitete Änderung an der Testkopie

`portal_adler/testing_mount.py` stellt ausschließlich nach dem expliziten Flag
ADLER_ISOLATED_TEST=True einen WSGI-Mount für /demo/ki-adler-portaltest bereit.
Es gibt keine automatische Registrierung in der produktiven App. Der normale
Adapter bleibt unverändert am Root betreibbar.

- Eigener Cookie-Name ki_adler_portaltest_session und Cookie-Pfad nur im Testpräfix.
  Die produktive Session wird nicht gelesen oder überschrieben.
- Alle per url_for erzeugten Ressourcen und Portalmenüs erhalten SCRIPT_NAME.
- Das Panel liest den Präfix aus seinem Template statt einen Rootpfad anzunehmen.
- Root außerhalb des Mounts liefert nur die lokale, synthetische Healthanzeige;
  andere ungemountete Pfade geben 404 zurück. So bleibt der vorhandene Controller-
  Healthcheck möglich, ohne Root-Portalseiten zusätzlich zugänglich zu machen.
- Die in der Kopie bereits abgeschaltete PWA-Rootregistrierung bleibt abgeschaltet.

Noch nicht als Pi-Update geliefert: kontrollierte Übernahme dieses Mounts in die
bereits laufende Kopie mit Backup der drei Testdateien, aktualisierten Codehashes,
angepasstem Runner und Rückkehr zur vorherigen Testkopie. Der bisherige Installer
bleibt auf seinem bekannten Stand gepinnt und holt diese Dateien nicht automatisch.
Kein zweiter Aufbau und keine zweite Datenbank sind dafür erforderlich.

## Freigabeablauf

1. Vorschau auf dem Pi erzeugen und statische Abschlussmeldung bestätigen lassen.
2. Mount-Update für die bestehende Testkopie konkret vorbereiten, sichern und lokal
   prüfen; kein Produktiv-Portalcode wird ersetzt.
3. Konkrete Nginx-Änderung zur Freigabe vorlegen. Erst nach ausdrücklicher Freigabe
   exakten alten Hash prüfen, Sicherung erstellen, nginx -t und kontrollierten
   Reload durchführen; bei Fehlern Original wiederherstellen und erneut prüfen.
4. HTTPS-Probe auf den ausschließlich synthetischen Test und anschließend iPhone-
   Abnahme: Menülinks, zwei Testkonten getrennt, Text stumm, Mikrofon/Replay/Stop,
   Schließen, Cookies und Root-Portal-Anmeldung unabhängig.

Noch keine Zustimmung zur Änderung des laufenden Webservers liegt für diesen
konkreten Block vor. Diese Vorschau ist deshalb ausdrücklich keine Aktivierung.

## Nachweise und offene Abnahme

156 pytest-Tests bestanden: 143 bestehende und 13 neue Parser-/Mount-/Cookietests.
Chromium 375/1280 sowohl am Root als auch unter dem Präfix bestanden, einschließlich
Text stumm, simulierter Sprache, Replay, Schließen und Textfallback.
Zusätzlich wurde die tatsächliche private Portal-Kopie mit den neuen Dateien lokal
unter dem Präfix geprüft: fünf echte Jugendseiten und authentifizierte Ergebnis-API
bestanden, ungemounteter Jugendpfad verweigert, PWA-Registrierung deaktiviert.
Weder Originalportal noch aktive Pi-Testkopie wurden hierfür verändert.

Keine echte Nginx-Syntaxprüfung, HTTPS-Freischaltung, iPhone-Speech-Abnahme oder
Pi-Mountprüfung behauptet. Rücknahme dieses PR vor einem Deployment: keine Aktion
am Pi nötig. Die private Vorschau kann liegen bleiben; keine Dienste hängen davon ab.

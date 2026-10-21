# Prüfbericht Vereinsbegleiter – 21.10.2026

## Bestand und Umfang

Ausgangsstand PR #12 `ab23d25109dbf86070c3755014810e22d7872ae1` geprüft:
weiterhin offen, Zielbranch PR #11, nicht ungeprüft als auf main angenommen.
Auf diesem Stand separater Branch `ki-adler/vereinsbegleiter`. Bestehender privater
Portalexport ausschließlich in bereits isolierter Kopie genutzt. Kein Export,
keine echten QR-Codes, Mitgliederlisten oder Datenbanken veröffentlicht.

Änderungen: eigener freundlicher Avatar, persönliche QR-Zuordnung mit lokaler
Vorname-Anzeige, Jugend-/Erwachsenentrennung, vorhandene lesende Ergebnis-/Kalender-
und Abzeichenfunktionen, auswählbare TTS-Stimme, explizite Spracheinwilligung,
Begrüßung, optionaler echter Modelladapter sowie ein reversibles Bestandsupdate.
Keine Datenbankmigration, keine neue Benutzerverwaltung, keine Nginx-/Pi-Änderung.

## Tatsächlich ausgeführte Prüfungen

- **212 pytest-Tests bestanden**, keine übersprungenen Tests im abschließenden Lauf
  mit erlaubten lokalen Testsockets. Darunter 27 bestehende Adaptertests und neue
  Tests für persönliche Begrüßung, Tokenkollision, getrennte Erwachsenen-Ergebnisse,
  Modellfreigabe/Einwilligung, Verlaufstrennung, fehlende Portalprofildaten im Payload,
  Widerruf nach langsamer Modellantwort, Providerfehler ohne vertrauliche Logs,
  HTTPS-/Redirect-/Größenlimits und sichere private Konfiguration.
- Chromium mit 375 und 1280 Pixeln, jeweils Root und isoliertem Testpräfix:
  Navigation und ursprüngliche Formulare vorhanden, Launcher per Hit-Test erreichbar
  oberhalb fester Navigation, Textfragen stumm, Replay, synthetische deutsche
  Spracheingabe, Stop/Close, Escape, fehlende Spracherkennung, keine horizontale
  Überbreite. Sprachdienste dabei durch kontrollierte Browserdoubles ersetzt.
- Tatsächliches Update einer bestehenden Cloud-Testinstallation mit der privaten
  Portal-Codekopie und ausschließlich künstlichen Konten auf 127.0.0.1:5071.
  Neue integrierte Prüfungen: echte Templates/Untermenüs, beide Konten, eigene
  Ergebnisse, Vorname, lokale Antwort auf „Wie geht es dir?“, vorhandene
  Abzeichenberechnung, WebP-Auslieferung, Ablehnung fremder IDs, getrenntes Cookie,
  Sperre bestehender Schreibaktionen.
- Wiederholter Updateaufruf ohne zweite Installation bestanden. Tatsächlicher
  Offline-Rollback inklusive SQLite und Code bestanden; vorheriger Testserver startet
  wieder, danach eigener Cloudprozess beendet. Fehlerwege synthetisch geprüft:
  fehlgeschlagener Selbsttest, später veränderte Dateien, vorhandene private
  Anbieterdatei und fremd belegter Port.
- Während der ersten realen Rücknahme wurde ein kurzer Abstand zwischen Prozessende
  und Socketfreigabe erkannt und behoben: begrenzt auf Portfreigabe warten, keinen
  fremden Prozess abschießen. Vollständige Wiederholung danach erfolgreich.
- Code-/Assetprüfsummen für Auslieferung und bekannten Vorgänger fest eingebaut.
  Öffentliche Quellcode-Dateien von privaten Export-/Laufzeitpfaden getrennt.
  Keine echten Passwörter, API-Schlüssel, QR-Zugänge, Datenbanken oder Audiodateien
  in den hinzugefügten Dateien. Testwerte sind ausdrücklich synthetisch.

## Messung und Grenzen

Cloud-Probelauf: vollständiges geprüftes Bestandsupdate einschließlich integriertem
Test und Start **1,625 Sekunden** in dieser vorbereiteten Cloudumgebung; Download und
vorherige Erstellung der Testumgebung nicht enthalten. Dies ist **keine Pi-3-Messung**
und keine Zusage zur Antwortzeit. WebP-Atlas 177.422 Byte; kein zusätzliches JavaScript-
Framework, kein lokales LLM, kein Audio-Upload an die Flask-App.

Echte LLM-Latenz, erste hörbare Antwort und Modellqualität sind mangels freigegebenem
Anbieterkonto/-schlüssel nicht gemessen. Providertransport mit kontrollierten Antworten
getestet; kein behaupteter echter Cloudflare-Inferenztest. Bestehende reale iPhone-
Spracherfahrung des Betreibers ersetzt keine neue TTS-/UI-Abnahme. Native Safari-/PWA-
Mikrofon-, Autoplay- und Stimmenrestriktionen bleiben Gerätetests.

## iPhone-Abnahme nach genau einem Testupdate

1. Bestehenden künstlichen persönlichen Testlink in Safari neu laden. Der freundliche
   Adler erscheint oberhalb der Navigation. Kein neuer Demo-Zugangscode erforderlich.
2. Adler öffnen: „Hallo, Testkind 1!“ bzw. zweites Testkonto. Alle bisherigen Menüs
   Start/Ergebnisse/Abzeichen/Termine/Kontakt bleiben erreichbar.
3. „Mein Training“, „Mein Fortschritt“, „Nächster Termin“, „Meine Abzeichen“ prüfen.
   Nur Daten des aktuellen künstlichen Kontos, keine Namen/Ergebnisse des anderen.
4. „Wie geht es dir?“ tippen: lokale freundliche Antwort, keine ungefragte Sprachausgabe.
   Beliebige andere Frage: ohne Anbieter ehrlicher Freischaltungshinweis.
5. „Vorlesen“ antippen; deutsche verfügbare Stimme wählen. Fehlt eine männliche Stimme,
   wird keine erfundene Stimme angeboten. „Stopp“ beendet Ausgabe sofort.
6. In Einstellungen Spracheingabe freiwillig erlauben, „Sprechen“ antippen, eine Frage
   stellen. Sichtbarer Zuhörstatus, danach Mikrofon aus und gesprochene Antwort soweit
   erlaubt. Berechtigung verweigern: Texteingabe bleibt nutzbar. Ohne Browser-API
   Tastaturdiktat verwenden und bei Bedarf Vorlesen antippen.
7. Beim Zuhören/Sprechen schließen, vollständig ausblenden, Safari wechseln und Seite
   verlassen: keine weitere Aufnahme/Ausgabe. Erneut öffnen: kein alter Gesprächsverlauf.
8. Große Ansicht, kleine Ansicht, Reduced Motion, Hoch-/Querformat und Bildschirmtastatur
   prüfen. Originalnavigation wird nicht ersetzt. Nach spätestens 15 Minuten neuer
   Zugang zum Gespräch erforderlich.
9. Erst nach gesonderter Anbieterfreigabe mit künstlichen Inhalten echten Modellaufruf
   testen; Provider-Ausfall darf das normale Portal nicht sperren.

Produktive Integration, individueller Betreuerzugriff, Schreibaktionen, OCR-Dialog,
Quiz/XP/Push und PWA-Gesamtabnahme sind damit nicht als fertig erklärt. Siehe
VEREINSBEGLEITER.md für verbleibende Abhängigkeiten und Freigaben.

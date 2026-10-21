# KI-Adler als persönlicher Vereinsbegleiter

Stand 21.10.2026. Aufbauend auf PR #7–#12, keine zweite Vereinsverwaltung.

## Was diese Version tatsächlich kann

- Vorhandene persönliche Jugend- und Erwachsenen-QR-Zugänge erkennen. Serverseitig
  aktives Konto nachschlagen, Vorname ausschließlich lokal begrüßen; kein Zusatzlogin.
  Ein QR-Code ist ein Zugangsschlüssel: Wer ihn besitzt, kann das zugehörige Portal
  öffnen. Er beweist keine physische Identität. Verlorene/geteilte Codes sperren bzw.
  rotieren; keine Codes in Analyse-/Proxy-Logs übernehmen.
- Nur eigene Ergebnisse, vergleichbaren Fortschritt und zielgruppengerechte Termine
  aus bestehenden SQLAlchemy-Modellen lesen. Kein Demo-/Mock-Ersatz für fehlende Daten.
  Vergleich nur bei gleicher Disziplin, Schusszahl und explizit gleicher Wertungsart
  an unterschiedlichen Tagen. Leere Wertungsart: keine Verbesserungsbehauptung.
- Jugendabzeichen über die vorhandene lesende Portalberechnung
  `get_abzeichen_status(member)`; keine eigene Vergabe oder zweite Regelverwaltung.
- Freundlicher eigener Adler nach Referenzvariante 1: grüne Augen, helles Gefieder,
  grünes Halstuch. Sechs leichte Bildzustände (177.422 Byte WebP), CSS-Bewegung,
  Reduced Motion und abschaltbare Animation. Schnabelbewegung wechselt während
  Sprachausgabe zwei Bilder; keine behauptete phonetisch genaue Lippensynchronisation.
- Einklappen, vergrößern und für den Seitenaufruf vollständig ausblenden. Stoppen,
  Schließen und Seitenwechsel beenden Mikrofon/Vorlesen und verwerfen die Anzeige.
  Originalnavigation bleibt vorhanden. CSS ausschließlich unter `#portal-adler`.
- Textchat, deutsche Browser-Spracherkennung nach freiwilliger Aktivierung,
  deutsche Systemstimmenauswahl, Replay und Stopp. Getippt bleibt stumm. Kein Wakeword,
  kein automatischer Mikrofonneustart und keine Hintergrundaufnahme. Fehlende API,
  verweigerter Zugriff und blockierte Ausgabe haben sichtbare Rückfallebenen.
- Echter austauschbarer OpenAI-kompatibler Dialogadapter mit kurzem flüchtigem
  Kontext. **Ohne eingerichteten und freigegebenen Anbieter kein freier LLM-Dialog.**
  Begrüßung/„Wie geht es dir?“ funktionieren lokal und sind als solche gekennzeichnet.
  Dies ersetzt kein frei dialogfähiges Modell.

## QR-Identität und Berechtigungen

`init_portal_adler` verwendet die vorhandenen Modelle. Jugend und Erwachsene haben
getrennte Namensräume und Ergebnis-Fremdschlüssel. Kollidiert derselbe Token in beiden
Tabellen, wird er abgelehnt. Pro Anfrage Aktivstatus, Tokenfingerabdruck und gebundene
Session prüfen. Client-IDs/Rollen akzeptiert die API nicht. Ein anderer Browser-Tab
kann mit alter Bindung weder Daten des neuen Kontos lesen noch dessen Sitzung schließen.
Das bestehende gemeinsame Betreuerpasswort wird ausdrücklich nicht als individuelle
Adminidentität aufgewertet. Sichere Betreuer-Schreibfunktionen bleiben ausstehend.

Die Templatefunktion wird additiv in der vorhandenen Basisvorlage aufgerufen. Nur
berechtigte persönliche `jugend_*`/`erwachsen_*`-Ansichten zeigen das Panel. Öffentliche
Demoansichten mit Token `demo` erhalten keine echten Daten. Kein offener öffentlicher
Allgemeinchat in diesem Schritt. Gemeinsamer Flask-Session-Schlüssel, exakte HTTPS-Origin,
CSRF-Header, Secure/HttpOnly/SameSite und ausdrücklicher Tokenreview sind Pflicht.

## Datenschutz und KI-Grenze

Die KI erhält keinen Datenbankzugriff und keine Tools/Schreibrechte. Eigene Ergebnisse,
Abzeichen, Vorname, Geburtstag, QR-Token und Bindung werden nicht automatisch in den
externen Gesprächsverlauf kopiert. Der allgemeine **Nutzertext kann trotzdem persönliche
Angaben enthalten**; eine Checkbox ist keine vollständige datenschutzrechtliche Freigabe.
Deshalb erst Betreiberprüfung/AVV/Rechtsgrundlage/Alterskonzept und klare Anbieteranzeige,
danach explizit aktivieren. Keine automatische Zusicherung, dass ein Anbieter für
Minderjährige geeignet ist. Prompt Injection kann keine zusätzlichen Datenrechte
freischalten. Modelltexte werden als Text angezeigt, nicht als ausführbarer HTML-Code.

Keine Audio- oder Chatdateien. Höchstens sechs Verlaufseinträge je gebundener Sitzung
im Prozessspeicher, höchstens 256 Sitzungen. Absolute Sitzungslaufzeit 15 Minuten ist
strenger als eine verlängerbare Inaktivitätsfrist. Ein gemeinsamer leichter Daemon-Timer
entfernt abgelaufene Kontexte auch ohne weitere Anfrage. Sofortiger Widerruf beim
Schließen; die Widerrufsroute funktioniert auch bei erreichtem Anfragelimit.
Ein bereits gestarteter HTTPS-Aufruf kann durch Browser-Abbruch nicht rückwirkend
zurückgeholt werden; Antworten werden nach Widerruf/Tokenwechsel/Ablauf verworfen.

Maximal 300 Zeichen, 2-KiB-JSON, 30 Anfragen/Minute/IP, zwei gleichzeitige Modellaufrufe
pro Workerprozess, zehn Sekunden Provider-Timeout, 64-KiB-Providerantwort, 1.200 Zeichen
Anzeige. Keine Weiterleitungen mit API-Schlüssel. Providerfehler/Antwortinhalte und
private Fragen werden nicht protokolliert. Mehrere WSGI-Prozesse benötigen eine spätere
gemeinsame begrenzte Sitzungsablage; jetzt ein Waitress-Prozess mit Threads.

## Anbieteroption ohne verpflichtende Zahlung

Am 21.10.2026 anhand offizieller Dokumentation geprüft:

- Cloudflare Workers AI: Free-Plan mit 10.000 Neurons pro Tag, Reset 00:00 UTC;
  bei Überschreitung im Free-Plan Fehler statt behaupteter unbegrenzter Nutzung.
  Bezahlte Modelle/Tarifwechsel und andere Cloudflare-Produkte sind gesondert zu prüfen.
  Kein Konto/Schlüssel ist hier angelegt, kein echter Inferenzaufruf wurde durchgeführt.
- OpenAI-kompatibler Endpunkt:
  `https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/v1/chat/completions`.
  Beispielmodell laut offizieller Kompatibilitätsdokumentation:
  `@cf/meta/llama-3.1-8b-instruct`. Modell und aktuelles Kontingent im Betreiberkonto prüfen.
- Laut Data-Usage-Dokumentation keine Verwendung von Customer Content für Training;
  gewöhnliche zustandslose Inferenz ohne Inhaltsaufbewahrung über die Verarbeitung
  hinaus, vorbehaltlich beschriebener Ausnahmen. Betriebsmetadaten können verbleiben.
  Kein AI Gateway mit Logging/Caching und keine zustandsbehafteten Speicherfeatures
  einschalten. Das allein ersetzt weder AVV noch Prüfung von Verarbeitungsregion,
  Drittlandtransfer, Modelllizenz und Minderjährigenschutz.
- Eigener leistungsfähiger HTTPS-Modellserver mit kompatiblem Endpunkt ist austauschbar.
  Kein großes LLM wird auf dem Pi 3 installiert; auch ein eigener Server ist kein
  pauschales Versprechen kostenloser Hardware oder ausreichender Geschwindigkeit.

Quellen: [Preise](https://developers.cloudflare.com/workers-ai/platform/pricing/),
[Datenverwendung](https://developers.cloudflare.com/workers-ai/platform/data-usage/),
[API-Kompatibilität](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/).

## Ein vorhandenes Testportal aktualisieren

Das Skript `scripts/update_companion.py` ist ausschließlich für den bereits aufgebauten
synthetischen Portaltest `/home/pi/ki-adler-portaltest` auf **5071**. Kein Neuaufbau,
kein pip-Installieren, keine neue DB. Es prüft die bekannte Installationssteuerung,
Runner- und alte Assethashes, sichert Code/private Konfiguration und SQLite, stoppt
nur den eigenen verifizierten Testprozess und startet ihn nach integrierten Tests.
Bei Fehler Rückweg; mit `--rollback` offline rücknehmbar. Bei fremden Änderungen
anhalten statt überschreiben. Die vorhandene Konfiguration des Vereinsportals bleibt
unberührt. Ports 5000/5057, Nginx und systemd werden nicht geändert.

Den unten im PR/der Auslieferungsnachricht angegebenen **festen Commit-Link** herunterladen
und ohne sudo als `pi` ausführen. Nicht alte Einzelreparaturen nochmals abarbeiten.
Vorhandene persönliche künstliche Testlinks bleiben gültig; im Safari-Tab neu laden.

```sh
python3 /home/pi/update_companion.py
```

Rückweg:

```sh
python3 /home/pi/update_companion.py --rollback
```

Das neue private `/home/pi/ki-adler-portaltest/private/dialogue.json` startet mit
Anbieter `off`, Freigabe `false` und leerem Schlüssel. Das Beispiel
`portal_adler/dialogue.example.json` enthält keine Zugangsdaten. Nach gesonderter
Anbieterfreigabe ausschließlich privat konfigurieren, Modus `compatible`, exakten
Endpunkt/Modell und eingeschränkten Schlüssel setzen; Datei muss Eigentümer `pi` und
Rechte 600 behalten. Niemals diese Datei auf GitHub oder im Chat veröffentlichen.
Anschließend ist ein kontrollierter Neustart **nur des Testprozesses** erforderlich;
die bestehenden Start/Stop-Befehle aus der Testinstallation verwenden.

## Produktive Integration und offener Umfang

Dieses Update ist keine Freigabe zur Übernahme nach `/home/pi/schuetzenjugend`.
Vorher: echtes Schema und aktuelle Portaldateien mit Export abgleichen, konsistentes
Backup/Restore, Tokenreview und Proxylog-/PWA-Cacheprüfung, individuelle Betreuerrollen,
Safari-Abnahme und explizite Produktivfreigabe. Kein Import der produktiven `app.py`
für eine „Prüfung“: ihr Import führt Schema-/Seed-Schreiboperationen aus.

Danach additiv Modelle und vorhandene lesende Abzeichenfunktion verdrahten, Helper
in Basisvorlage einfügen, Adapterpaket bereitstellen. Keine Menü-/Tabellenersetzung.
Rücknahme: Featureflag aus bzw. vorigen Codebestand zurückspielen; keine neue Migration.

Noch nicht umgesetzt: bestätigte An-/Abmeldung, Betreuerverwaltung per KI, OCR-Upload-
Dialog mit Bestätigung, Quiz/XP/Push, Beitragsveröffentlichung und gemeinsame PWA-Abnahme.
Vorhandene Portalmenüs für Ergebnisse/OCR/Abzeichen bleiben weiterhin maßgeblich.
Diese Funktionen werden nicht durch Antworttexte oder zusätzliche Schattenkonten simuliert.

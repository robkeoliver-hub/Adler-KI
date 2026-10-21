# Erster kleiner Phase-1-Schritt: widerrufbarer RAM-Kontext

## Problem und Verhalten

Vorher entfernten Logout und Ablauf nur die Referenz im Registry-Dictionary. Eine laufende KI-Anfrage hatte noch einen Verweis auf den alten Zustand, schrieb ihren Verlauf erneut hinein und lieferte eine Antwort aus, obwohl die Sitzung bereits widerrufen war. Der Cleanup-Worker konnte die Löschung um sein festes 30-Sekunden-Intervall verzögern.

Neu kapselt `adler/sessions.py` den rein flüchtigen Sitzungslebenszyklus. Logout, erfolgreiche Neuanmeldung, Ablauf und Shutdown leeren die vorhandene Verlaufsliste und markieren den Zustand als widerrufen. Dadurch werden auch Referenzen bereits laufender Requests entwertet. App-Lock schützt Registry und Verlauf.

Chat prüft zu Beginn, unmittelbar vor einem Provideraufruf und beim atomaren Freigeben der Antwort, ob Registry-Eintrag, Zustandsobjekt, Ablaufzeit und der zu Requestbeginn serverseitig erfasste Principal noch übereinstimmen. Bei Abmeldung, Sitzungstausch, Ablauf oder geändertem Subject/Rolle wird keine verspätete Antwort freigegeben und kein Verlauf zurückgeschrieben (HTTP 401). Ein bereitgestellter Text kann nach dem Freigabezeitpunkt bzw. bereits erfolgter Netzübertragung naturgemäß nicht zurückgerufen werden.

Ein schlafender Worker wartet höchstens bis zur nächsten tatsächlichen Ablaufzeit, bei früherem Login-/Logout-Wechsel wird er geweckt. Kein Timer je Mitglied, kein weiteres Programm und kein DB-Zugriff. Es gibt keine beabsichtigte zusätzliche 30-s-Aufbewahrung. Betriebssystem-/Interpreter-Scheduling ist kein Echtzeitsystem; Python garantiert keine physische Überschreibung kurzlebiger Request-/String-/Netzwerkpuffer. Eine bereits an einen Anbieter gesendete Anfrage kann dieser Patch nicht extern zurückrufen.

## Lebenszeit und bewusst enger Umfang

`SESSION_TTL` ist als Integer auf 1–900 Sekunden begrenzt. Die Demo verwendet weiterhin standardmäßig eine feste maximale Loginzeit von 15 Minuten ab Anmeldung; weder Polling noch neue Chatnachrichten verlängern diese Zeit. Damit liegt auch die Kontextdauer nach der letzten Aktivität höchstens bei 15 Minuten, kann aber früher enden. Eine gleitende Portalsitzung mit getrenntem Inaktivitäts-Kontext kommt erst zusammen mit nachgewiesener gemeinsamer Authentifizierung; hier entsteht keine neue Benutzerverwaltung.

Kein neuer Datenadapter, keine produktiven Mitgliederzugänge, kein öffentlicher Allgemeinchat, kein LLM-/Sprachdienst aktiviert, keine UI-/Menüänderung, kein PWA-/Avatarumbau und keine Schreibwerkzeuge. Diese Funktionen sind separat in TICKETS.md priorisiert. Die in der Bestandsaufnahme genannten übrigen Risiken sind nicht durch diesen kleinen Patch erledigt.

## Installation / Konfiguration / Migration

Nur auf separater Testinstanz: diesen Folgebranch auschecken, vorhandene virtuelle Umgebung mit requirements-dev.txt verwenden und Tests starten. Auf der bestehenden Pi-Testinstallation **nichts** automatisch auschecken, neu starten oder konfigurieren. Der Folge-PR basiert auf `ki-adler/isolierte-demo`, weil PR #1 noch nicht gemergt ist. Für einen isolierten Test ist ein leerer Arbeitsordner ohne produktive config.ini vorgesehen.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Unter Windows dieselben Pythonmodule über `.venv\Scripts\python.exe` starten; realer Windows-Betriebstest steht aus. Keine neuen Umgebungsvariablen, Zugangsdaten oder Datenbankmigrationen erforderlich. INI-Setup und Loopback-Bindung bleiben kompatibel. Umgebungsvariablen/Produktivmodus sind Ticket P1-02.

## Prüfung

- Ausgangsstand: 25 Tests bestanden.
- Aktueller Stand: **45 Tests bestanden**, letzter dokumentierter Lauf 1,29 s unter Python 3.12/Linux-Cloud, einschließlich 20 neuer Prüfungen.
- Sechs parallele Provider-Regressionsfälle: Logout, Neuanmeldung, Ablauf, Rollenwechsel, Subjectwechsel und Shutdown während aktiver Anfrage. Eventgesteuert, keine lange Wartezeit; erwartete Antwort 401, kein zurückgegebener Sentinel und keine wiederhergestellte History.
- Weitere Tests: keine Providerübertragung nach bekanntem Widerruf im Preflight, bestehende History-Referenzen gelöscht, Cookie erneuert, abweichender Registry-Zustand nie autorisiert, exakte 900-s-Grenze, nächster Cleanup-Zeitpunkt statt 30-s-Nachlauf und unzulässige TTL-Werte.
- Ein tatsächlicher schlafender Cleanup-Thread entfernt einen Ein-Sekunden-Testkontext ohne weiteren HTTP-Request; kontrollierter Shutdown im Test.
- Python compileall und node --check bestanden; keine Frontenddatei geändert.
- Chromium-Browser-Smoke (375/1280 Pixel) erneut ausführen: Login, lokale Demoantworten, simulierte Sprachfreigabe/TTS, Stopp, stumme Texteingabe, sichere Textanzeige und Logout. Reale iPhone-Sprachausgabe weiterhin nicht bestätigt.
- Erneuter Waitress-/Loopback-Benchmark: je zwölf Anfragen, Mock-Median 1,19 ms / p95 1,70 ms; lokale Antworten Median 1,11 ms / p95 1,19 ms. Cloud-/Netzwerkmessung, kein Pi-/Sprachversprechen und keine belastbare Vorher-/Nachher-Bewertung dieser kleinen Stichprobe.

## Manuelle Regression und Rollback

Auf Testinstanz Demo öffnen, anmelden, Text- und Sprachfallback prüfen, Gespräch beenden, mit gleichem Code neu anmelden: alter Chat bleibt leer. Für die deterministische Race-Reproduktion `tests/test_session_lifecycle.py` verwenden, keinen langsamen externen Dienst und keine echten Kinderdaten einsetzen. Echte Portalmenüs lassen sich erst mit aktuellem Portal-Adapter integrieren; in diesem PR sind Originalportal/Navigation unverändert und werden nicht als integriert getestet ausgegeben.

Rollback vor Deployment: PR nicht mergen bzw. Folgebranch verlassen; keine DB-/Dateneffekte. Falls später ausdrücklich auf einer Testinstanz ausgerollt: vorherigen bekannten Commit `072f2d28cc254d7c4883d23fc07dd8a0887d84e3` verwenden und ausschließlich den separaten Testdienst nach Freigabe neu starten. RAM-Kontexte gehen dabei erwartbar verloren. Kein Eingriff in Portal-Port 5000 und kein produktiver Rollback ohne gesonderte Freigabe.

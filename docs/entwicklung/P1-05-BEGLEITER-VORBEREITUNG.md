# P1-05: ein-/ausblendbarer Begleiter – unabhängige UI-Vorbereitung

## Tatsächlich umgesetzt

Die vorhandene isolierte Demo zeigt dieselbe Chat-/Sprachoberfläche zusätzlich innerhalb eines optional ein-/ausblendbaren Bereichs. `templates/_companion.html` ist eine kleine Jinja-Makro-Hülle, `static/companion.js` steuert ausschließlich Darstellung und Escape/Fokus, `static/companion.css` adressiert ausschließlich Elemente unter data-adler-shell. Kein globaler Menü-/Button-/Body-Reset in diesem neuen Wrapper. Die bestehende Demoansicht ist zunächst offen; die Hülle lässt sich in Tests auch geschlossen rendern. Es gibt kein zusätzliches Konto, keine Verwaltungsseite, keine neue Datenquelle und keinen neuen Anwendungs-Endpunkt.

Beim Ausblenden sendet die Hülle ein internes Ereignis an den bestehenden Chatcontroller. Dieser stoppt Browser-Spracherkennung und Vorlesen, bricht ausstehende Fetches ab und entwertet späte Callbacks. Erneutes Einblenden startet weder Mikrofon noch Replay noch neue API-Anfragen. Toggle hat aria-controls/aria-expanded, mindestens 44 Pixel Höhe und sichtbaren Tastaturfokus. Escape wirkt nur innerhalb des offenen Begleiters; Fokus kehrt zum Toggle zurück. Keine Speicherung des Sichtbarkeitszustands in localStorage/Cookie. Der Verlauf bleibt nur in der bestehenden begrenzten RAM-/DOM-Sitzung und wird durch Logout/Ablauf wie bisher gelöscht. Ausblenden ist kein Logout. Der Browserabbruch kann eine bereits auf dem Server oder beim Anbieter laufende Anfrage nicht zurückrufen; deren kurzlebiger Kontext bleibt an dieselbe begrenzte Sitzung gebunden.

Die ursprünglichen Chat-Elemente, Textfragen, Tap-to-talk, Freigaben und Stop bleiben erhalten. Getippte Fragen bleiben stumm. Ohne JavaScript ist der Toggle nicht als funktionsloser Button sichtbar; die Hostnavigation und Hostformulare bleiben unabhängig nutzbar. Auch die Mikrofon-Audioübertragung wird durch diesen Schritt nicht freigeschaltet: vorhandene gesonderte Freigaben bleiben nötig.

## Nachgewiesen / nicht nachgewiesen

- 76 pytest-Tests bestanden: 74 Konfigurations-/API-/Session-/Providerprüfungen plus zwei Template-/Komponentenprüfungen.
- Chromium 375/1280 Pixel: vorhandener Demo-Smoke plus Ausblenden während Zuhören und TTS, Rückkehr des Fokus, kein automatischer Neustart und keine Ausgabe verspäteter Sprachantwort nach Hide/Reopen. Speech ist dabei simuliert, keine echte Apple-Audioverbindung.
- Eine klar als synthetisch bezeichnete **Testhülle** mit Start/Ergebnisse/Abzeichen/Termine und einem neutralen Formular funktioniert mit geöffnetem/geschlossenem Begleiter und deaktiviertem JavaScript. Toggle führt keine API-Anfrage aus, Escape/Fokus geprüft. Diese Hülle existiert ausschließlich in tests/fixtures und dem Testskript, nicht als neue Portalroute oder zweite Vereinsverwaltung.
- Python-/JavaScript-Syntax geprüft. Keine neue Abhängigkeit, keine Modell-/Datenanbindung und keine Änderungen am Pi.

**Nicht integriert:** aktuelle Portalbase/Nav-Templates fehlen weiterhin. Tests mit einer Testhülle beweisen nicht, dass alle tatsächlichen Portalmenüs/-Formulare bereits abgenommen sind. Ticket P1-05 bleibt teilweise offen, P1-03/04 bleiben blockiert. Reale Portalrollen/SSO, echte Daten, freundlicher neuer Avatar, Replay-/Stimmwahl, fortlaufendes Gespräch und gemeinsame PWA sind nicht erledigt. Die Produktionsstartsperre aus P1-02 bleibt unverändert wirksam.

Die neue Hülle ist wiederverwendbar, die bisherigen großen Demo-Dateien adler.css/adler.js dagegen **nicht** blind in das Portal kopieren: deren globale Styles/DOM-IDs müssen beim tatsächlichen Einbetten überprüft/gekapselt werden. Einbinden erst mit AuthAdapter und bekannten Templates. Niemals den Demo-Code an echte Profile anschließen. Benötigte Quellen stehen in PORTAL-INTEGRATIONSBEDARF.md.

## Setup und Test

Nur isolierte Arbeitskopie dieses Folgebranches; requirements-dev.txt installieren, `python -m pytest -q`, auf einem separaten Entwicklungsrechner optional Playwright/Chromium installieren und `python tests/browser_smoke.py --engines chromium` ausführen. API-/Sessionkonfiguration bleibt kompatibel; keine Migration und keine neue Umgebungsvariable. Der Browser-Smoke richtet seine Fixture-Routen nur im Testprozess ein.

Manuell: Demo öffnen, Zugang öffnen, zuhören/vorlesen lassen und KI-Adler ausblenden. Mikrofon/Ton müssen stoppen. Wieder öffnen: kein ungefragtes Mithören, Textgespräch weiterhin bedienbar. Normale Menüs erst an der aktuellen Portal-Testkopie umfassend abnehmen. Reales iPhone-TTS und Android/iOS-PWA offen.

## Abhängigkeit / Zusammenführung / Rollback

Dieser Folgebranch basiert auf dem Konfigurationsbranch (PR #3), der auf #2 und #1 aufbaut. Kleinster Reviewdiff enthält nur die UI-Hülle, Ereignisanbindung, Tests und diesen Fortschritt. Für vollständige Kombination von oben nach unten mergen: optionaler UI-Schritt → #3 → #2 → #1, jeweils Test und Review; alternativ den UI-Schritt separat zurückstellen. Kein Merge/Deployment durch diesen Arbeitsauftrag. Vor Übernahme Basisköpfe erneut prüfen, Merge-Commit-Historie erhalten und Diffs nach Base-Wechsel kontrollieren.

Rollback ohne Deployment: Folge-PR nicht übernehmen. Nach späterem genehmigtem Testdeployment Wrapper-/Asset-Einbindung und Ereignislistener gemeinsam im Review-Revert zurücknehmen; klassische Demo ist der Basisstand. Keine DB-Rückmigration, keine Änderung von Mitgliederdaten, kein produktiver Dienstneustart ohne gesonderte Freigabe.

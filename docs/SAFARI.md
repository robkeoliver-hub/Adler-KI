# Sprache und iPhone-Abnahme

Recherche 21.10.2026, beide Seiten tatsächlich abgerufen:
- https://webkit.org/blog/11648/new-webkit-features-in-safari-14-1/ : Safari ab 14.1 bietet Spracherkennung über die Siri-Engine. Laut Hersteller muss Siri in den iOS-/iPadOS-Einstellungen aktiviert sein.
- https://caniuse.com/speech-recognition : partielle Unterstützung via webkitSpeechRecognition, Siri erforderlich; Einschränkungen für SafariViewController und zum Home-Bildschirm hinzugefügte Web-Apps. Versionsabhängige Angaben ersetzen keinen Gerätetest.

Die Demo prüft SpeechRecognition/webkitSpeechRecognition, sicheren Kontext und Standalone-Modus. Erkennung nur nach Antippen und expliziter Bestätigung des möglichen Browser-Sprachdienstes, de-DE, ein Durchlauf, maximal zwölf Sekunden, keine Dauererkennung und kein Wakeword. Die App verwendet weder MediaRecorder noch Audio-Upload und speichert keine Aufnahmen.

Fallback bei fehlender API oder Laufzeitfehler: Text tippen oder bewusst iPhone-Tastaturdiktat verwenden. Tastaturdiktat ist ein Geräte-/Apple-Dienst und wird wie Texteingabe behandelt: niemals automatisch vorlesen. Kein schwerer Transkriptionsdienst auf dem Pi. Siri/Browseranbieter können Audio extern verarbeiten; deshalb ist Spracherkennung standardmäßig aus und es sollen nur erfundene Testangaben gesprochen werden.

Vorlesen benötigt eine eigene Freigabe, nutzt speechSynthesis und bevorzugt eine deutsche localService-Stimme. Stimmen werden beim Sprechen erneut abgefragt. Qualität und Startfähigkeit hängen von Gerät, installierten Stimmen und Safari ab. Bei Fehler oder verzögertem Start bleibt die Textantwort verfügbar. Asynchrone Sprachausgabe kann auf iOS blockiert werden; ohne echten iPhone-Test keine Hörbarkeitsgarantie.

## Checkliste auf echtem iPhone (noch offen)
Datum, Modell, iOS-Version, Netz und Stimme festhalten. Keine echten Kinderdaten.

- [ ] Separaten HTTPS-Demo-Host direkt in Safari öffnen; Zertifikat gültig und public_origin passend.
- [ ] Hoch-/Querformat und 320–430 CSS-Pixel: kein Überlauf, Eingabe mit offener Tastatur erreichbar, Buttons mindestens 44 px hoch.
- [ ] Zugangscode, alle vier Beispielfragen und freie Folgefrage testen; Mock-Kennzeichnung sichtbar.
- [ ] Text und iPhone-Tastaturdiktat bleiben stumm, auch nach vorangegangener Sprachfrage.
- [ ] Ohne Sprachfreigabe startet die Mikrofontaste keinen Dienst.
- [ ] Mit Siri, HTTPS und Freigabe: Antippen startet deutsche Erkennung, Status deutlich sichtbar, Mikrofon danach aus.
- [ ] Zweites Antippen, Stopp, Tabwechsel und Zwölf-Sekunden-Grenze beenden Erkennung.
- [ ] Mit Vorlesefreigabe: deutsche Stimme; Stopp unterbricht sofort und keine späte Antwort beginnt erneut zu sprechen.
- [ ] Vorlesefreigabe aus: auch Sprachfrage erhält nur lesbare Antwort.
- [ ] Berechtigung verweigern, Siri deaktivieren, Netzwerk trennen, keine Sprache sprechen: klare Meldung und Textfallback.
- [ ] Home-Screen-Modus und eingebetteten Browser separat prüfen; Safari/Tippen als Fallback.
- [ ] VoiceOver, größere Schrift und „Bewegung reduzieren“ prüfen.
- [ ] Ende löscht Verlauf; nach 15 Minuten neue Anmeldung; Zurücknavigation zeigt keinen alten Verlauf.
- [ ] Netzwerkinspektor: keine Drittressourcen im Mock, kein Audio an die Demo; Apple-Sprachdienste gesondert berücksichtigen.
- [ ] Zehn Sprachversuche messen: Ende der Frage bis Textantwort UND bis erstes hörbares Wort, jeweils Median und p95. Hardware und Provider dokumentieren.

Ein echter iPhone-Test ist hier nicht durchgeführt. Desktop-WebKit ist kein Ersatz.

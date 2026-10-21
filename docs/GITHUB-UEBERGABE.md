# GitHub-Übergabeprüfung

Geprüft am 21.10.2026. Übernahme ausschließlich aus der geprüften Standalone-ZIP, nicht aus dem gesamten Arbeitsverzeichnis.

- Private config.ini mit zufälligem Demo-Zugangscode ausgeschlossen; Abgleich des tatsächlichen lokalen Codes gegen sämtliche Lieferdateien ohne Fund.
- Keine API-Schlüssel oder privaten Schlüssel nach gängigen Token-/Schlüsselsignaturen gefunden. Beispielkonfiguration enthält nur Platzhalter und leere Schlüsselwerte.
- Keine echten Datenbanken: Dateinamen und SQLite-Dateisignatur geprüft, keine Treffer. Original-Portal und Uploads werden nicht übernommen.
- Keine echten Mitgliederdaten in den Quellen oder Screenshots enthalten. Jugendprofil, Ergebnisse, Termin und Test-Zugangswerte sind ausdrücklich synthetisch. Quellen, Texte und Vorschau stammen aus der zuvor geprüften Demo. Keine E-Mail-Adressen gefunden.
- Synthetische Testcodes bleiben für reproduzierbare Tests enthalten. Sie sind keine gültigen Zugangsdaten eines laufenden Dienstes.
- .gitignore schließt private Konfiguration, Umgebungsdateien, Schlüssel, Datenbanken, Uploads, Laufzeitumgebung und Logs aus. Das ersetzt keine Prüfung neuer Dateien.
- Automatische Musterprüfung ist keine Garantie gegen beliebige zukünftige Geheimnisse. Vor jedem späteren Commit erneut prüfen.

Enthalten: vollständige Standalone-Quellen, Installation, sichere Start-/Stoppdateien, Tests, Sicherheitsanalyse, Inventar des Originals, Safari-Checkliste, Prüfbericht und Integrationsplan. Das Original-Inventar enthält nur Dateinamen, Größen, Hashes, Routen und Schemafelder, keine Datenbankinhalte.

Zielrepository: robkeoliver-hub/Adler-KI. Lieferung im separaten Branch ki-adler/isolierte-demo mit Pull Request zur Prüfung; kein automatisches Zusammenführen. Der von der Betreiberseite angelegte README-Startcommit auf main bleibt durch den Projektupload unverändert.

# Zusammenführung vorbereitet – kein Merge / kein Deployment

Geprüfter Stand 21.10.2026: PR #1 offen, `ki-adler/isolierte-demo` (`072f2d28cc254d7c4883d23fc07dd8a0887d84e3`) → main (`c332918d23680feb99fddf58ef0518b9e5cf1a98`); 33 Commits voraus, kein Rückstand. PR #2 offen, `ki-adler/phase01-sitzungsbasis` (`b28301922c2e74a514a27620d5d2803440aa978e`) → Demo-Branch; neun Commits voraus, kein Rückstand. Beide meldet GitHub als `mergeable=true`, `mergeable_state=clean`. Die PR-Beschreibungen wurden um Reihenfolge und Abhängigkeit ergänzt. Kein Branchkopf dieser beiden PRs und kein main wurde verändert.

Die 37 Dateien von PR #2 wurden lokal erneut mit den tatsächlichen Git-Blob-Hashes abgeglichen. Die Kombination ist damit genau der Snapshot aus #2 und bestand vor weiteren Änderungen 45 Tests. Das ist ein Cloud-Test, kein GitHub-CI- oder Pi-Nachweis. Konfliktfreiheit garantiert keine fachliche Produktionsreife.

## Reihenfolge

1. Sitzungskorrektur aus #2 zuerst in den Demo-Branch aus #1 übernehmen; Tests auf dem resultierenden Stand ausführen. Erst danach #1 nach main übernehmen. Dadurch erreicht main die Demo nicht ohne die bekannte Sitzungskorrektur.
2. Während Folge-PRs darauf aufbauen **Merge-Commits** verwenden, ursprüngliche Commits/Branches erhalten; kein Squash/Rebase/Branchlöschen mitten in der Kette. Sonst müssen abhängige PRs neu basiert und ihre Diffs geprüft werden.
3. Konfigurationsbranch `ki-adler/p1-02-konfiguration` baut ausschließlich auf dem geprüften PR-2-Head auf. Solange #2 offen ist, richtet sich sein kleiner PR auf diesen Branch. Er kann vor #2 in dessen Branch übernommen werden, anschließend die Kette von oben nach unten zusammenführen. Falls #1/#2 bereits per Merge-Commit nach main gelangt sind: Folge-PR auf main umstellen und sicherstellen, dass sein Diff nur die neuen Änderungen enthält.
4. Weitere kleine PRs nennen ihren tatsächlichen Basisbranch. Nach jedem Merge Base/Head neu abfragen, Tests, SHA256SUMS und Umfang prüfen. Keine automatisch aktivierte Mergefunktion oder ungeprüfte Zusammenführung.
5. Erst auf isolierter Testinstanz abnehmen: Anmeldungen/CSRF/Sessionwechsel, Text/Speech-Fallback, normale Menünavigation und keine synthetischen Daten im Produktivmodus. Der aktuelle Konfigurationsschritt verweigert Produktivstart ganz, bis Portaladapter geprüft sind.

## Vor dem tatsächlichen Merge prüfen

- Review der Sicherheitsbefunde und verbleibenden Blocker; kein CI-Erfolg behauptet, wenn nur lokale Tests vorliegen.
- Keine config.ini, Umgebungsgeheimnisse, echten DB-Dateien, Uploads oder Kinderdaten im Diff.
- API-/Sitzungs-/Konfigurationstests, Browser-Smoke und Syntaxprüfungen auf dem gemeinsam resultierenden Stand.
- Basisköpfe stimmen noch mit Prüfung überein; bei Änderungen erneut vergleichen.
- Die Mergefreigabe ist kein Auftrag für Git-Pull, Migration, Nginx-Änderung oder Neustart am Pi.

## Rollback

Vor Merge: einzelne Folge-PRs schließen oder Branch nicht verwenden; kein Laufzeiteffekt. Nach Merge: gezielter Revert im neuen Reviewbranch, keine History-Umschreibung. Da keine Schemaänderung vorliegt, ist keine Datenrückmigration nötig. Aktive Sitzungen sind nur RAM-Kontext. Änderungen eines Testdienstes oder produktiven Dienstes erfolgen erst nach ausdrücklicher Zielhostfreigabe. Der laufende Raspberry Pi bleibt in diesem Auftrag unverändert.

# Offline-Kalender

> **M10.3 Calendar-Slice:** Dieses Referenzbeispiel wird schrittweise von `legacy-readable-compatibility` auf die eingefrorene Revision-4-Zielsprache migriert. Parser-Lesbarkeit, kanonische Zielsyntax, Production Admission, runnable/generated Support und erwartete Ablehnung bleiben getrennte Aussagen. Dieser Calendar-only-Slice ändert weder den eingefrorenen Contract noch Python-Semantik, Production Admission oder zentrale Tooling-Logik.

Dieses Beispiel prüft Server-koordinierte Multi-Writer-Synchronisation:

- Events können mit clientgenerierter ID offline entstehen.
- Änderungen werden als typisierte Operationen protokolliert.
- Titel und Beschreibung verwenden servernormalisierte LWW-Metadaten.
- Teilnehmer verwenden ein Add-wins-Set.
- Start und Ende werden als atomare Konfliktgruppe manuell aufgelöst.
- Löschungen bleiben als Tombstone erhalten.
- aktuelle Serverberechtigungen werden bei jedem Push erneut geprüft.

Das Beispiel behauptet kein beliebiges Peer-to-Peer-CRDT. Der Server validiert
Invarianten und vergibt die kanonische Revision.

## M10.3 Calendar-Inventar und Disposition

Alle 13 committed `.aidl`-Dateien sowie die app-lokalen Erklärungs-/Lock-Flächen sind hier explizit disponiert. Eine lokale Quellmigration wird nur behalten, wenn die bestehende Parser-/Lint-/CI-Kette sie ohne zentrale Änderungen akzeptiert und sie keine neue Semantik erfindet.

| Pfad | M10.3-Disposition | Production-/Support-Grenze |
|---|---|---|
| `app.aidl` | unverändert Compatibility; Revision-4-Blockprofile wurden geprüft, aber in diesem Slice nicht behalten | `spec_lint` erkennt derzeit nur die historische Inline-Profilform und meldet bei kanonischen `profile name { version N }`-Slots leere App-Profile. Zusätzlich sind `system`, `frontend`, `api`, `defaultDeployment` und die inhaltlichen `auth`/`a11y`/`privacy`-Blöcke keine aktuelle produktive App-Oberfläche. |
| `domain/calendar.aidl` | unverändert Compatibility; Enum-`case` und Entity-`field` wurden geprüft, aber in diesem Slice nicht behalten | `spec_lint` erkennt bei kanonischen `field revision: revision ... concurrencyToken`-Slots das Concurrency-Token derzeit nicht. `value`, `union`, `view` und Invariant-Struktur liegen zudem außerhalb des aktuellen produktiven Envelopes. |
| `operations/calendar.aidl` | Query-Parameter auf den benannten HeaderArg `parameters: [...]` migriert | Diese Revision-4-Headerform passiert die bestehende Test-/Lint-Kette. `auth` und `consistency` sind dagegen keine Revision-4-Query-BodySlots; generische TypeRef-Argumente wie `Page<CalendarEventView>` bleiben in Production Normalization fail-closed. |
| `sync/calendar.aidl` | bewusst nicht als Produktionsbeweis umgeschrieben | Die `sync`-Familie ist nicht production-admitted; `for CalendarEvent` und der Sync-Body benötigen eine zentrale Contract-/Admission-Entscheidung oder bleiben non-production. |
| `system/api.aidl` | bewusst non-production | `api` ist nicht production-admitted und Revision 4 friert keine BodySlots für diese Produktstruktur ein. |
| `system/resources.aidl` | bewusst non-production | `resource` ist nicht production-admitted; Resource-Typheader und Body-Struktur sind keine aktuelle produktive Revision-4-Oberfläche. |
| `system/topology.aidl` | bewusst non-production | `service` und `system` sind nicht production-admitted; Ownership/Uses/Expose/Topology-Body benötigen zentrale Semantik. |
| `deployments/local.aidl` | bewusst non-production | `deployment` ist nicht production-admitted; `for CalendarSystem` und Deployment-Body sind nicht als aktuelle produktive Slots eingefroren. |
| `deployments/production.aidl` | bewusst non-production | Wie `local.aidl`; SLO/Autoscale/Secret-Bindings bleiben Produktvision, nicht Production-Admission-Evidenz. |
| `ui/app.aidl` | bewusst non-production | `theme` und `frontend` sind nicht production-admitted; deren Body-Struktur bleibt illustrative/Compatibility-Produktstory. |
| `ui/components.aidl` | bewusst non-production | `component` ist nicht production-admitted; Parameterheader und UI-Body sind keine aktuelle produktive Contract-Struktur. |
| `ui/pages.aidl` | bewusst non-production | `action`, `page` und `syncStatus` sind nicht production-admitted; Parameter-/UI-/SyncStatus-Bodies bleiben Produktstory. |
| `tests/calendar-sync.spec.aidl` | bewusst Test-/Produktstory-Evidenz | `test` ist nicht production-admitted; quoted test names, `target sync` und Test-Body sind keine aktuelle produktive Revision-4-Struktur und werden nicht in falsche positive Evidenz umgewandelt. |
| `README.md` | diese explizite M10.3-Disposition | Dokumentiert Support-Grenzen; erweitert den Contract nicht. |
| `aidl.lock` | unverändert | Der Grammar-Fingerprint beschreibt die globale normative Grammatik; Calendar-lokale Source-Migration ändert diesen Fingerprint nicht. |

## Zentrale M10.3-Grenze

Eine vollständige Calendar-Migration ist in diesem Parallel-Slice absichtlich nicht möglich. Es bestehen zwei getrennte zentrale Grenzen:

1. **Tooling-Akzeptanz der bereits eingefrorenen Zielsyntax.** `spec_lint` muss Revision-4-Blockprofile und explizite Entity-`field`-Slots semantisch äquivalent zur historischen Calendar-Schreibweise erkennen, bevor diese bereits kanonischen Formen im Referenzbaum dauerhaft migriert werden können. Dieser Slice darf `tools/**` nicht ändern.
2. **Semantik/Admission außerhalb des aktuellen Envelopes.** Für die verbleibende Produktgeschichte muss zentral entschieden werden, ob die betroffenen Strukturen dauerhaft non-production bleiben oder über einen separat versionierten Contract-/Python-Admission-Schritt eingeführt werden.

Von Grenze 2 betroffen sind insbesondere App-Verknüpfungen zu System/Frontend/API/Deployment, `value`/`union`/`view` und Invariants, Query-`auth`/`consistency` und produktive generische TypeRefs, Sync/API/Resource/Service/System/Deployment sowie Frontend/Theme/Component/Page/Action/SyncStatus und ausführbare AIDL-Testsemantik.

Bis zu solchen zentralen Entscheidungen bleiben diese Flächen parser-lesbare Compatibility-/Illustrative-Evidenz und dürfen weder als kanonisch vollständig migriert noch als production-admitted oder runnable/generated garantiert bezeichnet werden. Negative bzw. fail-closed Production-Normalization-Ergebnisse bleiben dabei gültige Evidenz und werden nicht durch Source-Umschreibung umgangen.

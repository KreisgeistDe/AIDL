# Offline-Kalender

> **Recovery R5 Authority:** Dieses Referenzbeispiel ist weiterhin ausdrückliche historische/Compatibility-Evidenz. Die aktive semantische Sprach-Authority ist `spec/core-self-description-v1.aidl`, interpretiert über `spec/bootstrap-kernel-v1.json`. Die nachfolgenden M10.3-/Revision-4-Dispositionen dokumentieren historische Kompatibilitäts- und Production-Grenzen; sie definieren keine aktuelle Core-Syntax. In diesem Slice wird keine `.aidl`-Quelle migriert.

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

Alle 13 committed `.aidl`-Dateien sowie README und Lock wurden gegen die auf `main` integrierte Shared-Authority `spec/m10-3-shared-disposition.json` erneut geprüft. Dauerhaft migriert werden nur die dort ausdrücklich als `supported-equivalent-source-form` freigegebenen Revision-4-Formen. Zentral disponierte Mismatches bleiben bewusst non-production/fail-closed; `app.links` bleibt der einzige hier relevante Fall mit `requires-versioned-admission`.

| Pfad | M10.3-Disposition | Production-/Support-Grenze |
|---|---|---|
| `app.aidl` | App-Profile auf kanonische Revision-4-Blockform `profile name { version N }` migriert | Nur die Profilform ist als äquivalente Source-Form freigegeben. `system`, `frontend`, `api` und `defaultDeployment` bleiben `app.links` und benötigen separat versionierte Admission; `auth`/`a11y`/`privacy` bleiben non-production/fail-closed. |
| `domain/calendar.aidl` | `CalendarEvent`-Felder auf kanonische explizite `field`-Slots migriert | Die Entity-Field-Form ist als äquivalent freigegeben und behält Revision-`concurrencyToken`-Checks. `value`, `union`, `view` und Entity-Invariants bleiben non-production/fail-closed; andere historische Schreibweisen werden nicht stillschweigend als neue Produktionssemantik umgedeutet. |
| `operations/calendar.aidl` | Query-Parameter bleiben auf dem benannten HeaderArg `parameters: [...]` | Diese Revision-4-Headerform ist kanonisch unterstützt. Query-`auth` und `consistency` sowie produktive generische TypeRefs wie `Page<CalendarEventView>` bleiben non-production/fail-closed. |
| `sync/calendar.aidl` | bewusst nicht als Produktionsbeweis umgeschrieben | `sync` ist zentral `non-production-fail-closed`; Sync-Header und -Body werden nicht durch lokale Umschreibung promoted. |
| `system/api.aidl` | bewusst non-production | `api` ist zentral `non-production-fail-closed`; die Produktstruktur ist keine aktuelle Production-Normalization-Evidenz. |
| `system/resources.aidl` | bewusst non-production | `resource` ist zentral `non-production-fail-closed`; Resource-Typheader und Body bleiben Produktstory. |
| `system/topology.aidl` | bewusst non-production | `service` und `system` sind zentral `non-production-fail-closed`; Ownership/Uses/Expose/Topology bleiben außerhalb der aktuellen Production Admission. |
| `deployments/local.aidl` | bewusst non-production | `deployment` ist zentral `non-production-fail-closed`; `for CalendarSystem` und Deployment-Body werden nicht promoted. |
| `deployments/production.aidl` | bewusst non-production | Wie `local.aidl`; SLO/Autoscale/Secret-Bindings bleiben Produktvision, nicht Production-Admission-Evidenz. |
| `ui/app.aidl` | bewusst non-production | `theme` und `frontend` sind zentral `non-production-fail-closed`; deren Body-Struktur bleibt illustrative/Compatibility-Produktstory. |
| `ui/components.aidl` | bewusst non-production | `component` ist zentral `non-production-fail-closed`; Parameterheader und UI-Body werden nicht als aktuelle Produktionssemantik behauptet. |
| `ui/pages.aidl` | bewusst non-production | `action`, `page` und `syncStatus` sind zentral `non-production-fail-closed`; UI-/SyncStatus-Bodies bleiben Produktstory. |
| `tests/calendar-sync.spec.aidl` | bewusst Test-/Produktstory-Evidenz | `test` ist zentral `non-production-fail-closed`; quoted test names, `target sync` und Test-Body werden nicht in falsche positive Produktions-Evidenz umgewandelt. |
| `README.md` | diese app-lokale M10.3-Disposition | Dokumentiert die integrierte Shared-Authority und erweitert den Contract nicht. |
| `aidl.lock` | unverändert | Der Grammar-Fingerprint beschreibt die globale normative Grammatik; diese äquivalenten app-lokalen Source-Formen ändern ihn nicht. |

## Integrierte Shared-Grenze

Die zentrale M10.3-Foundation ist inzwischen integriert. Sie erlaubt genau die in diesem Calendar-Slice verwendeten äquivalenten Quellformen: App-Profile-Blöcke, explizite Entity-`field`-Slots und den benannten Query/Mutation-HeaderArg `parameters`. Die Tooling-Checks behandeln diese Formen äquivalent zu ihren historischen Schreibweisen, ohne Production Admission, Canonical IR oder den eingefrorenen Revision-4-Contract zu verändern.

Die übrigen Calendar-Mismatches werden dadurch nicht positiv. Insbesondere bleiben App-Verknüpfungen zu System/Frontend/API/Deployment als `app.links` separat versionierungspflichtig. `auth`, `a11y`, `privacy`, `value`, `union`, `view`, Entity-Invariants, Query-`auth`/`consistency`, produktive generische TypeRefs, Sync/API/Resource/Service/System/Deployment, Frontend/Theme/Component/Page/Action/SyncStatus und AIDL-Testsemantik bleiben nach der gemeinsamen Disposition non-production/fail-closed.

Damit ist der Calendar-Slice hinsichtlich der aktuell zentral freigegebenen äquivalenten Source-Formen vollständig nachgezogen, aber **M10.3 insgesamt ist nicht abgeschlossen**. Negative bzw. fail-closed Production-Normalization-Ergebnisse bleiben gültige Evidenz und werden nicht durch Source-Umschreibung umgangen.

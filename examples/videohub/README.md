# VideoHub

> **M10.3 VideoHub-Slice:** Dieses Referenzbeispiel wird schrittweise von `legacy-readable-compatibility` auf die eingefrorene Revision-4-Zielsprache migriert. Parser-Lesbarkeit, kanonische Quellform, Production Admission, runnable/generated Support und Produktstory bleiben getrennte Aussagen. Dieser VideoHub-only-Slice ändert weder den eingefrorenen Contract noch Python-Semantik, Production Admission, Canonical IR oder zentrale Tooling-Logik.

VideoHub ist ein Architektur- und Konformitätsbeispiel für eine
YouTube-ähnliche Anwendung. Es demonstriert:

- getrennte Catalog-, Media-, Comment- und Search-Services,
- strikt getrennten Datenbesitz ohne serviceübergreifende ref-Felder,
- resumierbare Upload-Sitzungen und opake BlobHandles,
- Event/Outbox-getriebene Transcoding-Workflows,
- Worker-Queue und idempotente Verarbeitung,
- Renditions und CDN-Auslieferung,
- eventual konsistente Suchprojektion,
- Realtime-Kommentare mit Query-Fallback,
- View-Counter und Watch-Analytics-Stream,
- lokale und globale Deployments.

Der Transcoding-Algorithmus ist native, seine dargestellten Eingaben, Ausgaben,
Effects, Capabilities, Ressourcen und Fehler bleiben Produkt-/Compatibility-
Material und sind kein Beweis aktueller Production Admission.

VideoHub ist keine Behauptung, dass AIDL einen globalen Videodienst bereits
implementiert. Es zeigt die beabsichtigte Produktgeschichte, während M10.3 die
aktuell zugelassene Produktionsgrenze explizit und fail-closed hält.

## M10.3 VideoHub-Inventar und Disposition

Alle 25 committed `.aidl`-Dateien sowie README und Lock wurden gegen die auf `main` integrierte Shared-Authority `spec/m10-3-shared-disposition.json` geprüft. Dauerhaft migriert werden in diesem Slice nur deren drei `supported-equivalent-source-form`-Klassen: App-Profile-Blöcke, explizite Entity-`field`-Slots und der benannte Query/Mutation-HeaderArg `parameters`. Andere Oberflächen bleiben unverändert und werden nicht als neue Produktionssemantik interpretiert.

| Pfad | M10.3-Disposition | Production-/Support-Grenze |
|---|---|---|
| `app.aidl` | 6 App-Profile auf `profile name { version N }` migriert | Nur die Profilform ist äquivalent freigegeben. `system`/`frontend`/`api`/`defaultDeployment` bleiben `app.links` und benötigen versionierte Admission; `auth`/`a11y`/`privacy` bleiben non-production/fail-closed. |
| `contracts/analytics.aidl` | unverändert | `value` bleibt non-production/fail-closed. |
| `contracts/events.aidl` | unverändert | `event` und `topic` bleiben non-production/fail-closed. |
| `contracts/identifiers.aidl` | unverändert | `opaque` ist keine der drei freigegebenen äquivalenten Source-Formen und bleibt Compatibility-/Produktstory, nicht Production-Evidenz. |
| `contracts/media.aidl` | unverändert | `media`/`rendition` sind keine freigegebenen äquivalenten Source-Formen und bleiben Compatibility-/Produktstory. |
| `contracts/search.aidl` | unverändert | `value` bleibt non-production/fail-closed. |
| `deployments/global.aidl` | unverändert | `deployment` bleibt non-production/fail-closed; Regions-, Placement-, Binding-, Observability- und SLO-Struktur wird nicht promoted. |
| `deployments/local.aidl` | unverändert | `deployment` bleibt non-production/fail-closed. |
| `domain/catalog.aidl` | Felder von `Channel` und `Video` auf explizite `field`-Slots migriert | Entity-Field-Schreibweise ist äquivalent freigegeben; Revision-`concurrencyToken` und ref-Modifikatoren bleiben erhalten. `value`, `view`, Entity-Invariants und produktive Generic-TypeRefs bleiben non-production/fail-closed. |
| `domain/comments.aidl` | `Comment`-Felder auf explizite `field`-Slots migriert | Nur die Entity-Field-Schreibweise wird migriert; `value` und `view` bleiben non-production/fail-closed. |
| `domain/errors.aidl` | unverändert | `error` bleibt non-production/fail-closed. |
| `domain/media.aidl` | `MediaAsset`-Felder auf explizite `field`-Slots migriert | Nur die Entity-Field-Schreibweise wird migriert; `value`, `view`, Entity-Invariant und produktive Generic-TypeRefs bleiben non-production/fail-closed. |
| `operations/analytics.aidl` | Query/Mutation-Header auf `parameters: [...]` migriert | Headerform ist äquivalent freigegeben. Operation-`auth`/`cache`/`consistency`/`idempotency` bleiben fail-closed; Projection-Bodies bleiben Compatibility-/Produktstory und werden nicht als neue Semantik admitted. |
| `operations/catalog.aidl` | alle Query/Mutation-Header auf `parameters: [...]` migriert | Headerform ist äquivalent freigegeben. Operation-`auth`/`cache`/`consistency`/`idempotency`/`transaction`, produktive Generic-TypeRefs und zusätzliche Consumer-Produktlogik werden nicht promoted. |
| `operations/comments.aidl` | Query/Mutation-Header auf `parameters: [...]` migriert | Headerform ist äquivalent freigegeben. Operation-Ausschlüsse bleiben fail-closed; `channel`-Realtime-Struktur bleibt Compatibility-/Produktstory. |
| `operations/media.aidl` | Query/Mutation-Header auf `parameters: [...]` migriert | Headerform ist äquivalent freigegeben. Operation-Ausschlüsse und produktive Generic-TypeRefs bleiben fail-closed; `task`, Workflow-Body, Consumer- und `native function`-Struktur bleiben Compatibility-/Produktstory. |
| `operations/search.aidl` | Query-Header auf `parameters: [...]` migriert | Headerform ist äquivalent freigegeben. Operation-`auth`/`cache`/`consistency` und Generic-Return-Type bleiben fail-closed; Projection-Body bleibt Compatibility-/Produktstory. |
| `policies/access.aidl` | unverändert | `policy` bleibt non-production/fail-closed. |
| `system/api.aidl` | unverändert | `api` bleibt non-production/fail-closed; enthaltene Channel-Verknüpfung erweitert keine Admission. |
| `system/resources.aidl` | unverändert | `resource` bleibt non-production/fail-closed; Queue- und typisierte Resource-Produktstruktur ist keine aktuelle Production-Evidenz. |
| `system/topology.aidl` | unverändert | `service` und `system` bleiben non-production/fail-closed; Runs/Ownership/Dependencies/Channels werden nicht promoted. |
| `tests/videohub.spec.aidl` | unverändert | `test` bleibt non-production/fail-closed; Topology/Media/Failure/Projection/Realtime/Deployment-Szenarien sind Test-/Produktstory-Evidenz. |
| `ui/app.aidl` | unverändert | `theme` und `frontend` bleiben non-production/fail-closed. |
| `ui/components.aidl` | unverändert | `component` bleibt non-production/fail-closed. |
| `ui/pages.aidl` | unverändert | `page`, `form` und weitere UI-/Action-Struktur bleiben non-production/fail-closed bzw. Compatibility-Produktstory. |
| `README.md` | diese app-lokale M10.3-Disposition | Dokumentiert die integrierte Shared-Authority ohne Contract-Erweiterung. |
| `aidl.lock` | unverändert | Der Grammar-Fingerprint bleibt `sha256:487b3b985f5ddc1fcca5ef0949787d76b5754222ed1073aa6572b3278cea7fe5`; äquivalente app-lokale Source-Formen ändern ihn nicht. |

## Integrierte Shared-Grenze

Die zentrale M10.3-Foundation erlaubt für diesen Slice ausschließlich `app.profile-block`, `entity.field-slot` und `operation.parameters-header-arg` als äquivalente Revision-4-Quellformen. `app.links` bleibt separat versionierungspflichtig. Die zentral disponierten Familien und Clauses wie `auth`, `a11y`, `privacy`, `value`, `view`, Entity-Invariants, Operation-`auth`/`cache`/`consistency`/`idempotency`/`transaction`, produktive Generic-TypeRefs, `error`, `event`, `topic`, `policy`, `workflow`, `api`, `resource`, `service`, `system`, `deployment`, `frontend`, `theme`, `component`, `page`, `form`, `action` und `test` bleiben non-production/fail-closed.

VideoHub enthält darüber hinaus Produkt-/Compatibility-Oberflächen wie `opaque`, `media`, `rendition`, Realtime-`channel`, `task`, Queue-Struktur und `native function`, die in diesem Slice weder als neue Shared-Disposition erfunden noch in Production Admission aufgenommen werden. Sie bleiben unverändert und ausdrücklich keine positive Production-Normalization-Evidenz. Wenn diese Produktanforderungen später Produktionssemantik benötigen, ist dafür eine eigene explizite/versionierte Authority erforderlich.

Damit ist VideoHub hinsichtlich der aktuell zentral freigegebenen äquivalenten Source-Formen app-lokal nachgezogen. **M10.3 insgesamt bleibt offen**; negative, fail-closed und Compatibility-Ergebnisse bleiben gültige Evidenz und werden nicht durch Quellumschreibung umgangen.

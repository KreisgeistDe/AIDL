# Petstore

> **M10.3 Petstore continuation:** Nach Integration der Shared-Foundation sind die nachweislich äquivalenten Revision-4-Source-Formen für App-Profile und Entity-Fields dort kanonisiert, wo die bestehenden Petstore-Validierungspfade sie tatsächlich tragen. Die exhaustive dateiweise Disposition und die weiterhin fail-closed Grenzen stehen in [`M10.3.md`](./M10.3.md). Diese partielle Quellmigration ist keine pauschale Production-Admission.

Das Beispiel ist ein modularer, horizontal replizierbarer Petstore mit einer
lokalen SQL-Transaktionsgrenze.

Es demonstriert als **beabsichtigte Produkt-/Referenzgeschichte**, nicht als pauschale Production-Admission jeder verwendeten Sprachfamilie:

- OIDC-Identität ohne inkonsistente lokale User-Doppelung,
- explizite mutable/immutable-Felder und Revisionen,
- Compare-and-set gegen parallele Adoptionsanfragen,
- vollständige Idempotenz- und Fehlerverträge,
- atomare Outbox-Publikation,
- idempotenten Consumer als Workflow-Trigger,
- explizite Rückgabewerte,
- Web-UI mit stabiler Operation-ID und Conflict Handling,
- lokale und produktive Deployment-Profile,
- Concurrency-, Duplicate-Delivery- und Crashpoint-Tests.

PetstoreService besitzt alle fachlichen Entitäten. Das ist bewusst ein
modularer Monolith: Die Adoption aktualisiert Pet und AdoptionRequest in einer
einzigen lokalen Transaktion. Eine künstliche Trennung in Microservices würde
eine Saga erfordern und für dieses Beispiel keinen fachlichen Nutzen bringen.

## M10.3 Support-Grenze

Frozen M10.1 revision 4 bleibt die semantische Authority. Die integrierte M10.3-Shared-Disposition erlaubt am Shared-Parser/Lint-Boundary drei äquivalente Source-Formen: kanonische App-Profile, explizite Entity-`field`-Slots und benannte Query/Mutation-`parameters`-HeaderArgs. Dieser Petstore-Slice migriert App-Profile in `app.aidl` sowie Entity-Fields in `domain/adoptions.aidl` und `domain/pets.aidl`.

Der historische runnable Slice `m4-app/app.aidl` bleibt absichtlich unverändert: Exact-Head-CI zeigte, dass sein bestehender Production-Compiler-Pfad kanonische App-Profile noch mit `AIDL-DIST414` ablehnt. Shared Parser/Lint-Äquivalenz wird daher nicht fälschlich auf diesen Runtime-Pfad übertragen.

Die restlichen Grenzen bleiben unverändert:

- `app.links` (`system`, `frontend`, `api`, `defaultDeployment` und ähnliche App-Verknüpfungen) benötigt weiterhin eine separat versionierte Admission;
- auth/a11y/privacy sowie zahlreiche frozen-but-not-admitted Familien bleiben non-production/fail-closed;
- historische `auth`, `cache`, `consistency`, `idempotency` und `transaction` bei `query`/`mutation` bleiben außerhalb der zertifizierten Production-Normalization-Oberfläche;
- positional Query/Mutation-Signaturen bleiben in diesem Slice Compatibility-Input; das kanonische Ziel ist `parameters: [...]`;
- `m4-app/` bleibt konkretes runnable Compatibility-Evidence und kein Beweis für den gesamten Petstore-Sprachumfang.

M10.3/Petstore ist damit weiterhin **offen**.

## Struktur

~~~text
app.aidl
domain/
contracts/
operations/
policies/
system/
deployments/
ui/
tests/
m4-app/
M10.3.md
aidl.lock
~~~

## Prüfen

~~~bash
aidl check . --format json
aidl compatibility .
aidl plan . --deployment production
aidl test . --suite all
python3 ../../tools/spec_lint.py ../..
~~~

Ein grüner Tooling-Lauf hebt die M10.3-Dispositionsgrenzen aus `M10.3.md` nicht auf und ist keine implizite Production-Admission für frozen-but-not-admitted Sprachfamilien.

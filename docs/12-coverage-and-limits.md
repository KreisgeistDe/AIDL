# 12. Abdeckung und Grenzen

## Bewertungsmethode

Dieses Dokument trennt ausdrücklich drei Zustände:

- **spezifiziert**: Syntax/Vertrag ist in der AIDL-Spezifikation beschrieben;
- **compiler-/IR-belegt**: aktueller Compiler oder Canonical IR besitzt
  ausführbare Tests für den angegebenen Ausschnitt;
- **End-to-End-belegt**: Generator/Runtime/Adapter-Pfad ist zusätzlich in CI
  ausführbar nachgewiesen.

Eine breite Spezifikationsaussage ist kein Beweis für vollständige
Referenzimplementierung. Maßgeblich sind aktueller Code, Tests, maschinenlesbare
Verträge und die Roadmap in `TODO.md`.

## Aktuell belegter Implementierungsumfang

| Fähigkeit | Aktueller Repository-Beleg |
|---|---|
| Parser, Projektladen, Module, Imports, Symbole, FQN-Resolution | compiler-owned und regressionsgetestet unter `tools/` |
| stabile Diagnosen und M2-Semantikregeln | compiler-owned positive/negative Regressionen |
| Canonical IR | Version `0.3.0`, geschlossenes `spec/ir.schema.json`, deterministische Serialisierung |
| CLI `check`, `ir`, `plan`, `diff` | produktiv registriert und in CI getestet |
| Installierbares CLI-/Compiler-Artefakt | `pyproject.toml`, Wheel mit `aidl`-Entry-Point, gepinnte Runtime-Abhängigkeiten und isolierter Clean-Machine-Smoke |
| Agent-/IDE-Semantik | `inspect`, `dependencies`, `explain`, `summary`, `impact`, `resolve`, `complete`, `document`, `usages`, `rename` |
| Change-Kompatibilität | IR-Diff, vier Klassen und belegte Migrationshinweise |
| TypeScript/Fastify/PostgreSQL-Slice | begrenzter IR-only M4-Generatorpfad mit Ownership-Markern |
| Petstore-M4-Runtime | strict TypeScript build, Node-Tests, PostgreSQL-Migration/Startup und HTTP-E2E in CI |
| Golden Fixtures | Petstore plus gezielte Calendar-/VideoHub-Diagnostik-/Spezifikationsfixtures |
| IntelliJ | compiler-backed Diagnosen, Resolution, Completion, Documentation und Refactoring-Grenzen in Plugin-Tests |

Diese Tabelle beansprucht keine vollständige Implementierung sämtlicher
Deklarationen oder Profile. Insbesondere können Parser-/Diagnostikfixtures
breitere Spezifikationsflächen abdecken, ohne dass deren Semantik bereits in
Canonical IR, Generatoren oder Runtime materialisiert ist.

### Core-Supported-Coverage

Die folgende Tabelle wird aus `spec/core-conformance.json` und dem daraus abgeleiteten `spec/core-fixture-conformance.json` erzeugt. Nur Zeilen, deren Parse/Resolve/Validate/IR-Grenze nach dem versionierten Vertrag vollständig `implemented` oder `not-applicable` ist, erscheinen hier. `python3 -m tools.conformance_docs check` verhindert unabhängige manuelle Änderungen.

<!-- BEGIN GENERATED: core-supported-coverage -->
| Core Supported feature | Category | Parse | Resolve | Validate | Ir |
|---|---|---|---|---|---|
| `decl.alias` | declaration | implemented | implemented | implemented | implemented |
| `decl.api` | declaration | implemented | implemented | implemented | implemented |
| `decl.consumer` | declaration | implemented | implemented | implemented | implemented |
| `decl.entity` | declaration | implemented | implemented | implemented | implemented |
| `decl.enum` | declaration | implemented | implemented | implemented | implemented |
| `decl.error` | declaration | implemented | implemented | implemented | implemented |
| `decl.event` | declaration | implemented | implemented | implemented | implemented |
| `decl.mutation` | declaration | implemented | implemented | implemented | implemented |
| `decl.opaque` | declaration | implemented | implemented | implemented | implemented |
| `decl.query` | declaration | implemented | implemented | implemented | implemented |
| `decl.service` | declaration | implemented | implemented | implemented | implemented |
| `decl.topic` | declaration | implemented | implemented | implemented | implemented |
| `decl.transaction` | declaration | implemented | implemented | implemented | implemented |
| `decl.value` | declaration | implemented | implemented | implemented | implemented |
| `rule.api.exposure-version-compatibility` | rule | not-applicable | not-applicable | implemented | implemented |
| `rule.consumer.at-least-once` | rule | not-applicable | not-applicable | implemented | not-applicable |
| `rule.consumer.idempotency` | rule | not-applicable | not-applicable | implemented | implemented |
| `rule.entity.cross-service-ref-rejected` | rule | not-applicable | not-applicable | implemented | implemented |
| `rule.entity.owner-local-access` | rule | not-applicable | not-applicable | implemented | implemented |
| `rule.entity.single-owner` | rule | not-applicable | not-applicable | implemented | implemented |
| `rule.module.cyclic-dependency` | rule | not-applicable | implemented | implemented | not-applicable |
| `rule.module.duplicate-declaration` | rule | not-applicable | implemented | implemented | not-applicable |
| `rule.module.unresolved-name` | rule | not-applicable | implemented | implemented | not-applicable |
| `rule.mutation.required-clauses` | rule | not-applicable | not-applicable | implemented | not-applicable |
| `rule.mutation.single-root-effect` | rule | not-applicable | not-applicable | implemented | not-applicable |
| `rule.names.stable-fqn` | rule | not-applicable | implemented | implemented | not-applicable |
| `rule.query.side-effect-free` | rule | not-applicable | not-applicable | implemented | not-applicable |
| `rule.transaction.cross-resource-rejected` | rule | not-applicable | not-applicable | implemented | not-applicable |
| `rule.transaction.cross-service-rejected` | rule | not-applicable | not-applicable | implemented | not-applicable |
| `rule.transaction.outbox-atomic` | rule | not-applicable | not-applicable | implemented | implemented |
| `rule.transaction.resource-owner` | rule | not-applicable | not-applicable | implemented | implemented |
| `rule.types.int-to-decimal-only` | rule | not-applicable | not-applicable | implemented | not-applicable |
<!-- END GENERATED: core-supported-coverage -->

## Breiter Spezifikationsumfang

Die Spezifikation beschreibt Core, Web, Distributed, Offline, Cloud, Media und
Realtime. Die Profilregistry `spec/profile-registry.json` listet die
spezifizierten Profile, Deklarationsklassen und Validatornamen. Ihre Existenz
ist kein Conformance-Nachweis für alle Implementierungsschichten.

| Architekturklasse | Spezifikationsstatus | Implementierungsstatus |
|---|---|---|
| Core-Domäne, Queries, Mutations, Policies | breit spezifiziert | wesentlicher Compiler-/IR-Kern belegt; vollständige Core-Conformance bleibt M10 |
| Web-/UI-Verträge | spezifiziert | Parser-/Fixture- und IntelliJ-Anteile vorhanden; kein allgemeiner Web-Generator/Runtime |
| Services, Ownership, Topics, Outbox | spezifiziert | zentrale Compilerregeln plus begrenzter M4-Outbox-Pfad belegt; kein allgemeiner Distributed-Runtime-Stack |
| Sagas/Workflows/Consumer | spezifiziert | einzelne Compiler-/IR-Flächen vorhanden; produktionsfähige Distributed Runtime bleibt späterer Scope |
| Offline Sync/Konflikte | spezifiziert | gezielte Compiler-/Fixture-Abdeckung; keine vollständige Offline-Runtime |
| Cloud/Deployment | spezifiziert | Plan-/Fixture-Anteile vorhanden; keine produktionsreifen Provider-Adapter |
| Media | spezifiziert | Fixture-/Spezifikationsabdeckung; kein Media-Runtime-Pfad |
| Realtime | spezifiziert | Spezifikations-/Parseroberfläche; kein produktiver Realtime-Runtime-Pfad |

## Referenzanwendungen

### Petstore

Petstore besitzt den stärksten ausführbaren Beleg. Der begrenzte M4-Pfad prüft
Compiler, Canonical IR, Plan, TypeScript/Fastify/PostgreSQL-Generierung,
Ownership-Marker, strict build, Node-Tests, Migration/Startup und HTTP-E2E. Das
ist ein definierter Slice und keine Aussage, dass jede im großen Petstore-
Beispiel spezifizierte Oberfläche generiert oder ausgeführt wird.

### Offline-Kalender

Calendar Offline liefert aktuell vor allem Compiler-/Diagnostik- und
Golden-Fixture-Evidenz für den bereits unterstützten server-validierten
Sync-Kern. Vollständige Offline-Operation-Log-, Client-, Migration- und
Konvergenzruntime ist noch nicht implementiert.

### VideoHub

VideoHub liefert aktuell vor allem Spezifikations-/Diagnostik-Fixtures für
Ownership-, Media-, Topologie- und Deployment-Semantik. Transcoding,
Search-/CDN-/Realtime-Runtime und Provider-Deployment sind noch nicht als
End-to-End-Referenzpfad implementiert.

## Noch nicht als vollständiger Referenzpfad bewiesen

- vollständige Core-Conformance über Parse, Resolve, Validate, IR, Generate und
  IDE für jede als unterstützt bezeichnete Sprachfähigkeit;
- allgemeine Generator-/Runtime-Unterstützung außerhalb des begrenzten
  TypeScript/Fastify/PostgreSQL-M4-Slices;
- vollständige Distributed-, Offline-, Media- und Realtime-Runtimes;
- produktionsreife Provider-Adapter und Capability-Conformance;
- veröffentlichte Release-Artefakte, Checksums und Provenance;
- erzwungene Branch Protection auf `main`;
- repräsentative Performance-/Skalierungsgrenzen.

Der M9-04-Nachweis ist ausdrücklich eine lokale installierbare Packaging-
Baseline und noch keine veröffentlichte Release-Distribution. Der statische
`tools/spec_lint.py` bleibt ein Spezifikations-/Beispiel-Lint und ist kein
Ersatz für den Compiler. Umgekehrt existiert inzwischen ein echter
Compilerpfad; alte Aussagen, dieses Repository enthalte nur einen statischen
Linter oder noch keinen Parser/Resolver/Generator, sind nicht mehr zutreffend.

## Versions- und Coverage-Grenzen

Canonical IR, CLI-JSON-Schemas, Profilregistry und Distribution sind getrennte
Vertragsdomänen. Aktuell gilt:

- IR `0.3.0`, Schema-ID `https://aidl.example/spec/0.3/ir.schema.json`;
- CLI-JSON-Schema `7.0.0`, Schema-ID
  `https://aidl.example/spec/cli/7/cli-output.schema.json`;
- Profilregistry `registryVersion` `0.3.0`; Profil-Majors sind unabhängig und
  aktuell jeweils `1`;
- lokale `aidl-toolchain` Packaging-Baseline `0.0.0`, nicht veröffentlicht.

Keiner dieser Versionswerte allein bedeutet, dass sämtliche spezifizierten
Profile End-to-End implementiert sind.

## 1.0-Kriterien

Vor 1.0 müssen mindestens die in späteren Roadmap-Meilensteinen beschriebenen
Conformance-, Release-, Runtime-, Adapter-, Security- und
Kompatibilitätsnachweise erfüllt sein. Der aktuelle Pre-Release-Stand macht nur
Aussagen über explizit dokumentierte und ausführbar getestete Teilverträge.
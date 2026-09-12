# M10.5 — Kotlin Compiler-Core Migration Gate

## Purpose

M10.5 is an additive architecture and execution gate after the completed M10.1 freeze and the required M10.2/M10.3 pre-Kotlin source/documentation/example migration gates, before any further deepening of M11-04.1 dependency-aware incremental analysis or M11.5 unified compiler-service internals. It does not renumber, reopen, or reinterpret M1–M21 milestone identities or completion states. Existing completed M11-01 through M11-04 work remains completed; this gate controls only subsequent compiler-core investment.

M10.5 plans a staged migration of the compiler core from Python to Kotlin without a big-bang rewrite. Python remains the reference/conformance implementation until the explicit exit criteria below are met. No roadmap item in this gate by itself changes language semantics, conformance claims, Canonical IR, generator/runtime support, IDE support, release readiness, or public support status.

## Target architecture

The preferred target is Kotlin Multiplatform with one compiler-owned semantic interpretation:

- a platform-neutral Kotlin `common` compiler core for source model, parsing projection, resolution, typing, validation, diagnostics, Canonical-IR construction, compatibility-facing semantic facts, dependency/index relations, and deterministic query contracts where the used libraries permit true common code;
- a Kotlin/Native CLI target that does not require a JVM at runtime and is suitable for native distribution and startup-sensitive command-line workflows;
- a JVM target that reuses the same common compiler semantics for IntelliJ, LSP/JVM integration, tests, and other JVM-hosted adapters;
- thin platform adapters only for filesystem, process, transport, IDE protocol, and distribution concerns; adapters must not own divergent parser, resolver, type, validation, diagnostic, IR, or compatibility semantics.

A JVM-only rewrite is not the target architecture, and a Kotlin/Native fork with separate semantics is not acceptable. Platform-specific code may exist only where Kotlin Multiplatform requires it and must project the same compiler-owned contracts.

## Migration principles

- Python stays authoritative for conformance during migration and remains runnable in CI until Python exit criteria are satisfied.
- Kotlin work proceeds in independently reviewable vertical slices with differential evidence; no wholesale source-tree replacement is permitted.
- Existing schemas, diagnostic codes, Canonical-IR shapes, stable identities, ordering, compatibility classes, fixtures, and public CLI contracts are preserved unless a separately authorized language/schema decision changes them.
- A Kotlin implementation is not accepted because it compiles or reaches similar happy-path output. It must match observable compiler semantics and deterministic failure behavior.
- New Kotlin-core and critical compiler packages require at least 95% line/code coverage plus branch/condition coverage and explicit evidence for critical semantic paths. Trivial mock-, getter-, wiring-, or stub-only tests do not satisfy the gate.
- Coverage is necessary but not sufficient: differential parity, mutation/negative-path strength where practical, fixture breadth, branch/condition evidence, and semantic-path assertions are required.

## Dependencies and sequencing

The whole M10.5 migration, including M10.5-01, begins only after M10.3 is integrated. The required order is `M10.1 -> M10.2 -> M10.3 -> refreshed M10.5-01 -> M10.5-02 and later Kotlin work`.

M10.2 first classifies and aligns the complete committed source/documentation surface against the frozen M10.1 authority. M10.3 then migrates intended reference examples and explicitly resolves every production semantic mismatch, with any actual semantic/admission change requiring a versioned contract update, re-freeze, exhaustive coverage, and certification. M16.5 remains a later broader normalization/metamodel milestone and is not a substitute for these pre-Kotlin gates.

Current PR #77 and any pre-M10.2 M10.5-01 inventory/fingerprint are provisional/deferred evidence only. They cannot serve as the final Kotlin parity baseline. After M10.3 is integrated, M10.5-01 must be refreshed or rebased from the resulting Python reference state, its evidence inventory regenerated, and its deterministic fingerprint recomputed before M10.5-02 may begin.

Before additional M11-04.1 or M11.5 compiler-core architecture is implemented, the migration plan and parity harness defined here must be accepted so new cache/index/service architecture is not unnecessarily coupled to Python-only internals.

Completed M11-01 through M11-04 behavior is an input contract for migration parity. M11-04.1 and M11.5 may continue only where work is adapter-neutral or explicitly compatible with the shared target architecture; compiler-core deepening waits for the corresponding M10.5 gate.

## Phases

### M10.5-01 — Contract inventory and differential harness

M10.5-01 is executable only after integrated M10.3. Any earlier inventory or fingerprint, including PR #77's pre-M10.2 baseline, must be treated as provisional and refreshed against the post-M10.3 Python reference baseline before this phase can satisfy Gate 01.

- [ ] Inventory the Python compiler-owned semantic surface used by CLI, LSP, agent tools, fixtures, compatibility, and IntelliJ integration, including deterministic ordering, stable identities, source locations, diagnostic payloads, Canonical IR, and failure modes.
- [ ] Freeze a machine-readable parity corpus from existing Golden Fixtures, Core conformance evidence, negative diagnostics, Canonical-IR snapshots, reference applications, compatibility fixtures, and representative CLI inputs without inventing new support claims.
- [ ] Define normalized differential comparison rules for Python-versus-Kotlin outputs, explicitly listing any transport-only fields that may differ while rejecting semantic normalization that hides real divergence.
- [ ] Add a differential test runner design that can execute the same source/config/profile inputs through both implementations and compare diagnostics, Canonical IR, semantic identities, ordering, and exit behavior.
- [ ] Define version/fingerprint inputs for parity runs so compiler/schema/profile/config changes cannot accidentally compare mismatched contracts.

#### Gate 01

No Kotlin semantic implementation proceeds beyond scaffolding until integrated M10.3 exists and the refreshed parity corpus and differential comparison contract cover the supported Core source surface and the current completed M11 query behavior relevant to compiler semantics.

### M10.5-02 — Kotlin Multiplatform compiler skeleton

- [ ] Establish the Kotlin Multiplatform module boundaries for common compiler core, Kotlin/Native CLI adapter, and JVM adapter without moving semantic authority away from Python.
- [ ] Keep filesystem/process/protocol integration outside common semantic packages and document every unavoidable platform-specific boundary.
- [ ] Add deterministic serialization/test utilities required for byte- or structure-stable parity evidence.
- [ ] Enforce at least 95% code coverage for new Kotlin-core and designated critical compiler packages, plus branch/condition coverage reporting and critical semantic-path tests.

#### Gate 02

The common-core boundary must be demonstrably platform-neutral, with both Native and JVM targets consuming it and no duplicated semantic implementation hidden in adapters.

### M10.5-03 — Front-end parity slices

- [ ] Migrate parsing/source projection in bounded slices while Python remains the reference.
- [ ] Migrate module/import/name resolution and stable symbol/FQN identity in bounded slices.
- [ ] Migrate type construction, type checking, serialization checks, and materialization boundaries in bounded slices.
- [ ] For every slice, require Python-versus-Kotlin differential parity across positive fixtures, negative diagnostics, ordering, locations, and deterministic repeated runs before expanding scope.

#### Gate 03

The Kotlin front end must produce equivalent accepted/rejected source classification and equivalent stable diagnostics for the covered surface before Canonical-IR construction can become Kotlin-owned for that same surface.

### M10.5-04 — Canonical IR and semantic query parity

- [ ] Migrate Canonical-IR construction without changing the existing versioned schema or silently defaulting/dropping source facts.
- [ ] Prove full-document schema validity and deterministic structural equality against Python for the supported parity corpus.
- [ ] Migrate compiler-owned semantic queries needed by current CLI/LSP/agent behavior, including definition, completion, documentation, references, rename planning, fixes, inspect/dependencies/explain/impact where applicable.
- [ ] Prove cross-implementation identity and query equivalence for saved, unsaved-snapshot, and multi-root cases already guaranteed by completed M11 work.

#### Gate 04

Kotlin cannot become the default semantic implementation until diagnostics, Canonical IR, and the current compiler-owned query surface are reproducibly equivalent on the defined parity corpus.

### M10.5-05 — Native CLI, JVM integration, and operational parity

- [ ] Produce a Kotlin/Native CLI that runs the supported command surface without a JVM runtime dependency.
- [ ] Provide a JVM integration target for IntelliJ/LSP/JVM consumers that delegates to the same common compiler semantics.
- [ ] Differentially compare command exit codes, diagnostics, JSON contracts, Canonical IR, deterministic output ordering, and representative error handling.
- [ ] Define reproducible startup, throughput, memory, and artifact-size measurements for Python and Kotlin on controlled Small/Medium/Large workloads; uncontrolled wall-clock timing is not a CI gate.
- [ ] Establish native distribution packaging, checksums, architecture matrix, and clean-machine smoke requirements before any Python distribution path is retired.

#### Gate 05

Native and JVM adapters must demonstrate semantic equivalence and acceptable operational behavior without separate semantic caches/indexes or adapter-local interpretation.

### M10.5-06 — M11-04.1/M11.5 continuation on shared architecture

- [ ] Resume dependency-aware invalidation, cache/index, and unified compiler-service deepening only on abstractions compatible with the common Kotlin compiler target and the still-authoritative Python parity oracle.
- [ ] Centralize dependency/reverse-reference relations so the eventual Kotlin service does not reproduce Python-only index ownership in adapters.
- [ ] Require cached-versus-uncached and Python-versus-Kotlin equivalence for diagnostics, identities, queries, edit plans, cancellation, and stale-result suppression.
- [ ] Keep conservative fallback behavior whenever incremental precision is unavailable during migration.

#### Gate 06

No adapter may depend on an implementation-specific semantic shortcut that prevents Python/Kotlin differential execution or a single future Kotlin-owned compiler service.

### M10.5-07 — Python exit readiness

Python remains the reference/conformance implementation until every exit criterion below is met. Removing or demoting Python authority requires a dedicated reviewed change after this checklist is complete.

## Hard parity gates

Every migrated semantic slice must satisfy all applicable gates before it can replace Python for that slice:

1. **Golden Fixture parity** — existing positive and negative fixture corpus passes with equivalent accepted/rejected behavior.
2. **Diagnostic parity** — stable diagnostic code, severity, phase, subject identity, expected/actionability payload where applicable, source path/location, ordering, and deterministic repeated output are equivalent.
3. **Canonical-IR parity** — semantic structure, declaration IDs/FQNs, references, types, ordering, source mappings, and full schema validity are equivalent; no supported source fact is lost or defaulted differently.
4. **Differential parity** — automated Python-versus-Kotlin runs cover representative valid, invalid, boundary, multi-file, unsaved, multi-root, and reference-application cases.
5. **Coverage quality** — at least 95% code coverage for new Kotlin core and designated critical compiler packages, accompanied by branch/condition coverage and explicit critical-path evidence for parser recovery, resolution ambiguity, type errors, materialization rejection, diagnostic ordering, IR construction, cancellation/staleness, and incremental invalidation where implemented.
6. **Determinism** — repeated cold and warm runs over identical inputs produce stable semantic results independent of source enumeration order where the current compiler guarantees order independence.
7. **No mock-only closure** — parity gates must execute real compiler paths; mocks may isolate adapters but cannot stand in for parser/resolver/type/validate/IR semantics.

## Python exit criteria

Python may cease to be the reference/default compiler only when all of the following are measured and reproducibly satisfied:

- **Language-surface parity:** every source form currently accepted or rejected by the supported compiler/conformance surface has an equivalent Kotlin result, including stable behavior for unsupported/unmaterialized constructs.
- **Diagnostic parity:** the complete committed diagnostic corpus is reproducible in Kotlin with stable codes, locations, ordering, subjects, actionability/expected fields, and deterministic JSON/text projections where those are contracted.
- **Canonical-IR parity:** every accepted semantic fact required by current downstream tools is present with equivalent identities and ordering, and every emitted document validates against the same versioned IR schema.
- **Query parity:** current compiler-owned CLI/LSP/agent semantic queries and edit plans are equivalent for saved, unsaved, incremental, and multi-root scenarios covered by the existing test suite.
- **Conformance parity:** all existing Core conformance, fixture, compatibility, reference-application, Golden Fixture, and required compiler/CLI regressions pass against Kotlin; support manifests are not promoted merely because Kotlin exists.
- **Differential burn-in:** CI runs Python and Kotlin in parallel for an explicitly defined burn-in period/workload set with zero unexplained semantic mismatches before default authority changes.
- **Coverage quality:** new Kotlin core and designated critical compiler packages maintain at least 95% code coverage plus branch/condition and critical semantic-path evidence; excluded/generated code is documented and bounded rather than used to inflate coverage.
- **Performance/startup:** on a controlled benchmark environment, Kotlin/Native CLI startup and representative cold/warm compiler workloads meet published thresholds relative to the Python baseline with no material regression in memory bounds or deterministic structural work; thresholds must be recorded before the exit decision.
- **Native distribution:** supported native artifacts install and run without a JVM on the declared platform/architecture matrix, with reproducible packaging, checksums, version identity, and clean-machine command smokes.
- **JVM integration:** IntelliJ/LSP/JVM consumers use the same common semantics and pass existing integration tests without adapter-local semantic fallback.
- **Failure and fallback behavior:** malformed input, cancellation, stale snapshots, unsupported features, cache mismatch, and partial migration boundaries fail explicitly and deterministically; silent fallback that changes semantics is forbidden.
- **Rollback readiness:** the release that first defaults to Kotlin retains an explicit, tested rollback path to the last Python-reference release until post-cutover validation is complete.

## Completion criteria

M10.5 planning is complete when the architecture, phases, differential harness contract, hard parity gates, coverage-quality requirement, Python exit criteria, and mandatory dependency on integrated M10.3 are versioned in the roadmap and accepted without changing implementation or support claims.

M10.5 implementation is complete only after all phase gates and Python exit criteria are satisfied by executable evidence. Until then, Python remains the reference/conformance implementation and Kotlin migration work is incremental.

This milestone does not authorize Kotlin/build/compiler implementation by itself; implementation requires separately dispatched work packages after M10.3 and the refreshed M10.5-01 gate are complete.

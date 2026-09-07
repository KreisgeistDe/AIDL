# M17–M21 — Full specified-language coverage

These milestones close specification-to-roadmap gaps without changing the responsibilities or completion states of M1–M16. They are planning authority only. A roadmap item, documented syntax, or acceptance criterion is not evidence that a surface is implemented, supported, generated, deployable, or editor-complete. Implementation/support claims remain governed by `spec/conformance-manifest.json` and the applicable conformance matrices and executable evidence.

M12–M15 continue to own distributed/offline/media runtime vertical slices, provider adapters, ecosystem conformance, migrations, security, and release readiness. M17–M20 own language/compiler/IR contracts needed to express those specified capabilities coherently; M21 owns exhaustive language conformance certification.

## Milestone M17 — Extended Type System and Standard Library

Goal: implement and certify the specified Core type-system and standard-library surface that lies beyond the currently bounded Core subset.

Dependencies: M10 Core conformance authority and evidence machinery; M11 compiler-service work may improve execution performance but is not semantic authority.

- [ ] **P1** Inventory every specified scalar, constraint form, collection constructor, nullable/list/set/map composition, nominal alias/opaque behavior, and public serialization rule from `docs/01-core-language.md` against parser, resolve, validate, IR, generator, and IDE coverage.
- [ ] **P1** Implement constrained scalar forms and dimensions that are specified but not yet compiler-complete, including length/pattern/range/precision-scale constraints and dimension-safe duration/bytes/CPU/percent units.
- [ ] **P1** Implement the specified generic declaration surface for value, union, view, component, and native function, including allowed bounds, invariance, compile-time resolution, bounded expansion, stable public monomorphization, and rejection of unsupported generic forms.
- [ ] **P1** Complete discriminated-union, generic-view, alias, opaque, enum, Value field, nominal identity, and public-wire semantics across all required implementation layers.
- [ ] **P1** Implement and version the `aidl.std` contracts needed by the language: identity/time types, paging, standard errors, `Result`, `AsyncState`, idempotency context, media handles, sync values, realtime values, and UI semantic types.
- [ ] **P1** Define lockfile/profile/stdlib version-resolution behavior and diagnostics so the standard library remains independently versioned and reproducible.
- [ ] **P1** Add positive/negative fixtures, Canonical IR fixtures, compatibility evidence, generated-contract evidence where applicable, and compiler-authoritative editor evidence for every promoted M17 surface.

### M17 acceptance criteria

- [ ] Every type-system and standard-library construct claimed as supported has executable Parse/Resolve/Validate/IR evidence and applicable Generate/IDE evidence.
- [ ] Unsupported generic, constraint, serialization, or standard-library forms fail with stable diagnostics rather than degrading to generic named types or being silently discarded.
- [ ] Public generic instantiations and standard-library identities produce deterministic, versioned Canonical IR and stable compatibility facts.
- [ ] `spec/conformance-manifest.json` and any detailed conformance matrix are updated only for surfaces whose executable evidence satisfies the claim.

## Milestone M18 — Advanced Backend Language

Goal: make the backend DSL in `docs/02-backend.md` compiler-complete as language semantics, independently from M12–M15 runtime/provider delivery.

Dependencies: M17 for extended types/stdlib; M7 remains compatibility authority; M12 remains distributed runtime authority.

- [ ] **P1** Complete API surface semantics for REST/RPC/GraphQL, version/base path, auth/error modes, rate limits, compatibility modes, and transport-invariant nullability/error/paging contracts.
- [ ] **P1** Complete query contracts for typed filter/sort/page/stream boundaries, declared consistency, cache semantics, timeout/budget rules, ownership/projection reads, and bounded collections.
- [ ] **P1** Complete mutation contracts including public reasons, authorization, idempotency normalization/retention, root-effect exclusivity, direct idempotent resource calls, audit, timeout, and retry safety.
- [ ] **P1** Implement explicit read-only remote authorization semantics and diagnostics without treating it as a distributed transaction or invariant.
- [ ] **P1** Complete transaction semantics for supported isolation, optimistic CAS/revision flow typing, bounded pessimistic locks, invariant timing, resource ownership, rollback-visible local state, and atomic outbox publication.
- [ ] **P1** Complete policies, events, topics, consumers, queues, projections, workflow/saga, task, schedule, and native-function language contracts including retry, timeout, dead-letter, replay/rebuild, compensation, capabilities, determinism, and resource budgets.
- [ ] **P1** Materialize every accepted backend semantic fact required by planners, adapters, generators, compatibility analysis, and runtime validation in Canonical IR or reject the source construct explicitly.
- [ ] **P1** Add exhaustive backend diagnostics and layer evidence without claiming runtime behavior owned by M12–M15 until those runtime milestones provide their own evidence.

### M18 acceptance criteria

- [ ] Every backend declaration and clause in the supported M18 scope is either represented losslessly in Canonical IR or rejected with a stable compiler diagnostic.
- [ ] Planner/generator inputs can derive backend contracts solely from validated Canonical IR without reparsing syntax.
- [ ] Backend compatibility-sensitive facts remain classified by M7 rather than by generator/runtime adapters.
- [ ] No M18 completion claim implies a general distributed runtime, provider adapter, or production deployment capability.

## Milestone M19 — Frontend Language

Goal: implement the frontend DSL in `docs/03-frontend.md` as a typed, compiler-authoritative language surface without turning AIDL into JSX/CSS or conflating language support with a production UI runtime.

Dependencies: M17 type system/stdlib; M18 for referenced API/query/mutation contracts; M11 for compiler-authoritative editor behavior.

- [ ] **P1** Implement frontend declarations, targets, rendering modes, themes, locales, routes, auth guards, fallbacks, and platform capability/fallback rules.
- [ ] **P1** Implement typed design-token contracts and static validation for token-only styling, explicit visual overrides, contrast, and platform scaling constraints.
- [ ] **P1** Implement pure components and generic components, semantic elements, keyed repeat/render behavior, typed component/action values, and prohibition of direct persistence/topic/arbitrary-network effects.
- [ ] **P1** Implement page/data contracts including URL state, query-backed data, refresh triggers, consistency, stale/refreshing behavior, and required loading/empty/error states.
- [ ] **P1** Implement typed form/state lifetimes, secure local/session/replicated persistence rules, stable idempotency identities across retries, optimistic connected actions, offline queued actions, sync-status handling, and realtime subscribe/reconnect/resume/fallback contracts.
- [ ] **P1** Implement upload, accessibility, SEO, privacy, native-component capability, SSR/offline fallback, and audited-accessibility contracts with stable diagnostics.
- [ ] **P1** Define Canonical IR representation for frontend semantics and add platform-neutral generator contracts plus at least one bounded target adapter before promoting Generate claims.
- [ ] **P1** Add compiler-owned completion/navigation/documentation/refactoring evidence for promoted frontend constructs; editor-local interpretations remain forbidden.

### M19 acceptance criteria

- [ ] Supported frontend source is fully typed and represented in Canonical IR with no silent loss of state, consistency, accessibility, privacy, capability, fallback, or retry semantics.
- [ ] Invalid UI dataflow/effect/persistence/accessibility contracts produce stable compiler diagnostics independent of a target framework.
- [ ] At least one bounded target generator consumes only Canonical IR, while unsupported targets/capabilities fail explicitly.
- [ ] `profile.web` remains `specified` or `partial` until conformance evidence justifies promotion; M19 roadmap completion alone is insufficient.

## Milestone M20 — Distributed, Sync, Resource, Deployment, and Evolution Language Contracts

Goal: close language/compiler/IR gaps for architecture-heavy specified profiles while preserving M12–M15 ownership of runtimes, provider adapters, migrations, operations, and ecosystem certification.

Dependencies: M17–M19 as applicable; M7 remains semantic compatibility authority; M12–M15 remain runtime/ecosystem authorities.

### Distributed language surface

- [ ] **P1** Complete system/service/reliability/client/channel/tenant language contracts, ownership/access graphs, synchronous call-chain budgets, queue/topic/stream delivery, ordering, partitioning, deduplication, consistency, projections, saga/reservation, and redundant-execution constraints from `docs/07-distributed-systems.md`.
- [ ] **P1** Materialize service/resource ownership, reliability stores, delivery/partition/order/replay facts, projection rebuild prerequisites, channel resume/backpressure/fallback, tenant propagation, and service-identity/delegation facts in Canonical IR.

### Offline/sync language surface

- [ ] **P1** Complete sync modes, authority/scope, operation logs, push/pull, outbox change feeds, tombstones, causal clocks, conflict strategies/groups, deterministic custom merge, authorization revalidation, rejected-operation handling, attachment tickets, and local schema migration from `docs/08-offline-sync.md`.
- [ ] **P1** Enforce server-coordinated multi-writer boundaries and explicit rejection/profile separation for unspecified peer-to-peer/BFT/consensus semantics.

### Resource/deployment language surface

- [ ] **P1** Complete portable resource declarations for SQL/document/key-value/time-series/blob/CDN/cache/queue/topic/stream/search/counter/secret/config/local stores plus media contracts from `docs/09-resources-deployment.md`.
- [ ] **P1** Complete deployment topology, regions, residency, replicas, autoscale, health, rollout, shutdown, observability, SLO, failover, serverless/worker, secret/config, and provider-capability requirement semantics.
- [ ] **P1** Keep provider products out of application/system semantics; provider bindings must remain independently versioned capability evidence owned operationally by M14/M15.

### Evolution language surface

- [ ] **P1** Reconcile the specified evolution vocabulary in `docs/10-evolution-compatibility.md` with the implemented M7 compatibility authority; eliminate naming/semantic drift through a versioned compatibility contract rather than adding a second classifier.
- [ ] **P1** Complete language/IR contracts for event evolution/upcasts, database expand/backfill/contract migrations, projection/index migration, offline client-version windows, rolling deployment coexistence, deprecation lifecycle, and explicit data-loss decisions.
- [ ] **P1** Ensure `aidl diff`/compatibility/plan projections remain derived from M7-owned semantic facts and classifications.

### M20 acceptance criteria

- [ ] Every promoted Distributed/Offline/Resource/Cloud/Media/Realtime/Evolution language fact is compiler-validated and Canonical-IR materialized or explicitly rejected.
- [ ] The language can express the contracts required by M12–M15 without those runtime milestones redefining syntax or semantics.
- [ ] Runtime/provider conformance remains separate: M20 cannot promote general runtime, cloud-adapter, deployment, sync-engine, or media-processing support by itself.
- [ ] Compatibility classification has one semantic authority, with any terminology mapping versioned and regression-tested.

## Milestone M21 — Full-Language Conformance Closure

Goal: provide exhaustive, mechanically traceable conformance for the complete language/profile surface that the project chooses to claim as supported.

Dependencies: M10 conformance framework, M17–M20 language implementation, applicable M11 editor/compiler-service work, and runtime/generator evidence from M12–M15 where support claims require those layers.

- [ ] **P1** Extend machine-readable conformance coverage from Core-only detail to every supported profile/declaration/clause/rule with stable surface IDs and required layers.
- [ ] **P1** Define per-surface required layers instead of assuming every profile needs identical runtime/editor evidence; keep Parse/Resolve/Validate/IR mandatory for supported language semantics and require Generate/Runtime/IDE only where a public support claim includes them.
- [ ] **P1** Link every support claim to positive, negative, Canonical IR, compatibility, planner/generator/runtime, and editor evidence as applicable.
- [ ] **P1** Add deterministic full-language fixture inventories spanning type system/stdlib, backend, frontend, distributed, offline, resources/deployment, evolution, media, realtime, and representative cross-profile compositions.
- [ ] **P1** Certify that accepted source constructs do not lose semantic facts between parser, semantic model, Canonical IR, planning, generation, runtime adapters, compatibility analysis, or editor projections.
- [ ] **P1** Generate public support/coverage documentation from conformance authorities so roadmap prose and specifications cannot independently promote support status.
- [ ] **P1** Add explicit unsupported-surface fixtures and diagnostics for every specified-but-unimplemented construct retained in the language documentation.
- [ ] **P1** Establish a release gate that rejects unsupported support wording, stale evidence, orphaned matrix rows, non-executable claims, and profile-version drift.

### M21 acceptance criteria

- [ ] Every publicly claimed supported language/profile surface has machine-readable authority, stable status, and executable evidence for every applicable implementation layer.
- [ ] Every specified but unsupported surface is visibly classified and fails explicitly if accepted syntax would otherwise be silently ignored.
- [ ] Canonical IR contains every accepted semantic fact required by downstream supported tools across all claimed profiles.
- [ ] Public support documentation is generated or drift-checked from conformance authority; roadmap completion and specification prose cannot promote support claims.
- [ ] A full-language conformance run is deterministic in CI and produces a reviewable inventory of supported, partial, experimental, specified, blocked, and unsupported gaps.

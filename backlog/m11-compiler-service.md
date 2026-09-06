# M11 — Production language server and compiler service

## Milestone M11 — Production Language Server

Goal: provide editor-neutral, compiler-authoritative semantics for unsaved and multi-root workspaces.

- [x] **P1** Introduce an in-memory compiler snapshot API for authoritative unsaved-buffer analysis. *(M11-01 adds immutable compiler snapshots that combine deterministic saved-project discovery with explicit in-memory overrides, reuse the existing parser/project/type/diagnostic pipeline, carry resolve/completion/documentation queries over the same source texts, and make LSP diagnostics/definition authoritative on unsaved full-text buffers without adding workspace-ownership or incremental-state semantics.)*
- [x] **P1** Define deterministic workspace discovery, ownership, and multi-root behavior. *(M11-02 canonicalizes configured root order, assigns every source to the most-specific containing root before analysis, builds isolated per-root compiler snapshots, safely admits owned unsaved new `.aidl` files, and routes LSP diagnostics/definition through the owning snapshot so overlapping or independent roots cannot leak semantics.)*
- [x] **P1** Add incremental analysis, cache invalidation, watched-file handling, cancellation, progress, and lifecycle/load tests. *(M11-03 adds compiler-owned per-root snapshot caching keyed by exact deterministic source fingerprints, conservative root-level invalidation for saved/unsaved and watched-file changes, isolated caches, cancellation without cache/partial-result publication, balanced work-done progress, shutdown/restart state handling, and structural repeated-request load regressions without wall-clock gates.)*
- [x] **P1** Expose existing compiler-owned completion, documentation, references, rename, and authorized fixes through LSP. *(M11-04 exposes those capabilities over the owning incremental compiler snapshot, including unsaved buffers and isolated multi-root workspaces, with compiler-owned rename/fix authority and no editor-local semantic fallback.)*

### M11-04.1 — Dependency-Aware Incremental Analysis

- [ ] **P1** Replace root-wide rebuilds with dependency-aware module/declaration invalidation while retaining a conservative full-root fallback whenever dependency precision is unavailable.
- [ ] **P1** Add content-addressed parse reuse plus incremental resolve, type-check, validation, and diagnostic caches so unchanged semantic work is reused across requests.
- [ ] **P1** Key reusable analysis on exact source content plus compiler/schema/profile/configuration versions and dependency fingerprints; stale or mismatched keys must never be reused.
- [ ] **P1** Centralize reverse-reference and dependency indexes that drive invalidation, references, rename, impact, and affected-declaration queries from one compiler-owned relation.
- [ ] **P1** Extend cooperative cancellation into incremental parse/resolve/type/validate/index phases so cancelled work cannot publish partial caches, indexes, diagnostics, or edits.
- [ ] **P1** Make watched-file invalidation dependency-aware for edits, creates, deletes, and moves, with deterministic conservative fallback when ownership or dependency identity is uncertain.
- [ ] **P1** Prove cached and uncached analysis are semantically equivalent for diagnostics, completion, definition, documentation, references, rename planning, and authorized fixes.
- [ ] **P1** Instrument compiler phases and add reproducible cold/warm Small/Medium/Large benchmarks that report cache hits/misses, invalidated/reused units, rebuild work, and query counts without making uncontrolled wall-clock timing a CI gate.
- [ ] **P1** Publish controlled p50/p95 targets for diagnostics, completion, definition, references, and rename only from a defined benchmark environment and workload contract.
- [ ] **P1** Bound cache/index memory, cross-request reuse, and deterministic eviction; measure memory alongside latency and structural work so warm performance cannot grow state without limit.
- [ ] **P1** Add rapid-edit, repeated-cancel, delete/move, restart, and multi-root workspace-churn regressions covering cache correctness, invalidation, equivalence, memory bounds, and stale-result suppression.

### M11.5 — Unified Compiler Service Architecture

- [ ] **P1** Define one compiler-service API that owns project/workspace analysis and serves CLI, LSP, agent, and future protocol adapters without adapter-owned semantic state.
- [ ] **P1** Move lifecycle and cache/index ownership behind that service so adapters do not construct divergent compiler lifecycles or independently invalidate semantic state.
- [ ] **P1** Define transport-independent snapshot identity and lifecycle contracts, including freshness, ownership, cancellation, restart, and stale-snapshot rejection.
- [ ] **P1** Prohibit divergent adapter caches or semantic indexes; every adapter must reuse the same service-owned snapshot/cache/index interpretation.
- [ ] **P1** Add cross-adapter equivalence tests proving the same snapshot yields equivalent diagnostics, identities, queries, and edit plans through CLI/LSP/service consumers.
- [ ] **P2** Expose non-semantic service metrics for cache reuse, invalidation, rebuild work, memory, and query volume without allowing metrics plumbing to own language semantics.

### M11.6 — Agent Query Optimization

- [ ] **P1** Add batched compiler-service queries for inspect, dependencies, explain, and impact so agents can request bounded semantic context without repeated full-project setup.
- [ ] **P1** Return a stable snapshot fingerprint with agent query results and reject or explicitly mark requests/results that target a stale snapshot.
- [ ] **P1** Add affected-declarations and affected-files queries backed by compiler-owned dependency/reverse-reference indexes rather than repository-wide text scans.
- [ ] **P1** Add a conservative minimal-validation projection that identifies the smallest known validation scope for a change and falls back to broader validation whenever precision is uncertain.
- [ ] **P1** Reuse compiler-service snapshots and indexes across agent queries so repeated inspect/dependency/explain/impact work does not rebuild equivalent semantic state.
- [ ] **P1** Preserve deterministic bounds, totals, ordering, and truncation metadata for every batched or affected-set response.

### M11.7 — MCP Integration

- [ ] **P2** Add a thin, initially read-only MCP adapter over the unified compiler service; it must not become a second parser, resolver, validator, compatibility engine, or planner.
- [ ] **P2** Expose structured MCP tools for check, summary, inspect, dependencies, explain, impact, diff, and plan by projecting existing compiler/CLI/service contracts rather than reimplementing them.
- [ ] **P2** Reuse long-lived service snapshots and return their fingerprints so MCP clients can correlate results and detect stale project state.
- [ ] **P2** Define stable transport-independent request/result schemas and keep MCP transport errors distinct from compiler validation, resolution, compatibility, planning, and stale-snapshot failures.
- [ ] **P2** Add deterministic MCP contract, lifecycle, cancellation, stale-state, invalid-input, and cross-adapter equivalence regressions.
- [ ] **P2** Document the recommended MCP coding-agent workflow and its bounded context/query strategy.
- [ ] **P2** Keep all parser, resolver, type/validation, compatibility, planning, and fallback semantics out of the MCP adapter; unsupported service capabilities must fail explicitly rather than being guessed locally.

### M11.8 — Protocol Identity and Edit Preconditions

- [ ] **P1** Preserve compiler diagnostic codes, semantic identities, document/edit versions, and explicit edit preconditions across the protocol boundary.

### M11.9 — Optional LSP Protocol Library

- [ ] **P2** Select and pin an LSP protocol library only if it reduces protocol-maintenance risk without owning language semantics.

### M11.10 — Packaged Server and Client Smokes

- [ ] **P1** Add packaged server launchers and smoke tests for VS Code plus at least one of Zed or Neovim.

### M11 acceptance criteria

- [ ] Diagnostics, navigation, completion, references, rename, and fixes operate correctly on unsaved buffers.
- [x] Multiple workspace roots cannot leak declarations or edits across project boundaries. *(M11-02 assigns each source to exactly one most-specific root and constructs independent compiler snapshots before semantic analysis; cross-root imports/navigation remain unresolved and no cross-root edit authority is exposed.)*
- [ ] Editor clients consume one compiler-owned semantic interpretation with no client-local fallback semantics.
- [ ] Large-workspace latency, cancellation, memory, and restart behavior meet published baselines.

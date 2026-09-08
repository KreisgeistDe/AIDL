# Roadmap policy, Definition of Done, and execution order

## Implementation policy

`TODO.md` is the sole handwritten authority for roadmap order, milestone identity, and completion state. Operational execution state remains on `agents/channel`; committed legacy project `.ai/**` current-state files are not a second roadmap authority.

The project tree is intentionally `.ai/**`-free. Every project PR targeting `main` must reject any `.ai/**` endpoint, including additions, modifications, deletions, copies, and renames; the former one-time legacy deletion exceptions are obsolete because those files no longer exist in the project repository. Operational state and any maintenance of the transport workflow belong only in `KreisgeistDe/AIDL_channel@agents/channel`, never in a project PR.

`spec/conformance-manifest.json` is the separate authoritative versioned implementation/support source. New or changed support claims must update a stable manifest surface ID, use only the schema-defined status vocabulary, and carry repository-relative evidence that passes `python3 -m tools.conformance_manifest validate`. Roadmap completion alone never promotes a support claim.

The offline repository-state check `python3 -m tools.validate_repository_state` enforces the `.ai/**`-free project invariant and the roadmap, channel, and conformance authority markers. It requires no network access and runs in standard validation CI.

M10-01 records repository-level support surfaces only. M10-02 provides the exhaustive Parse/Resolve/Validate/IR/Generate/IDE matrix for every Core declaration and semantic rule; incomplete rows or evidence remain explicit in that matrix and must not be interpreted as full layer completeness. Public wording in `SUPPORT.md` is drift-checked against each manifest `supportStatement`.

The language specification is normative design input, not implementation status. Syntax or semantics documented in `docs/` remain **specified** unless conformance authority and executable evidence justify a stronger claim. Likewise, adding or completing M17+ roadmap tasks does not itself change `spec/conformance-manifest.json`, Core/profile conformance status, generator/runtime support, editor support, or release readiness.

M10.5 is an additive compiler-architecture migration gate after complete M10 Core-conformance closure and before further compiler-core deepening of M11-04.1 or M11.5. It does not renumber, reopen, or reinterpret existing M1–M21 milestone identities or completion states, and it does not itself authorize Kotlin/build/compiler implementation. Python remains the reference/conformance implementation during staged migration; Kotlin Multiplatform is the preferred target with a platform-neutral common compiler core, a Kotlin/Native CLI that requires no JVM at runtime, and a JVM target for IntelliJ/LSP/JVM integration. Every migration slice must preserve the existing language, diagnostics, Canonical-IR, compatibility, fixture, and public-contract authorities unless separately changed by an authorized semantic/schema decision.

M10.5 requires differential Python-versus-Kotlin evidence rather than a big-bang rewrite. New Kotlin core and designated critical compiler packages require at least 95% code coverage plus branch/condition coverage and explicit critical semantic-path evidence; mock-, stub-, wiring-, or happy-path-only coverage does not satisfy the gate. Python authority may be retired only after measured parity for supported language surfaces, deterministic diagnostics and Canonical IR, compiler-owned queries, the existing conformance/fixture/compatibility suites, controlled startup/performance/memory thresholds, native non-JVM distribution, JVM integration, failure/fallback behavior, and an explicit burn-in and rollback contract.

M16.5 is a planning/decision gate between agent-construction evaluation and broad M17–M20 language expansion. It is additive: existing M1–M21 milestone identities and completion states remain unchanged. M16.5 may inventory, compare, and approve future normalization candidates, but it does not itself define replacement syntax, alter parser/semantic/IR behavior, or authorize a breaking source change. Any compatibility-sensitive normalization requires a separate versioned language decision plus M7-owned compatibility classification, migration/deprecation evidence, implementation, fixtures, and conformance updates.

M17–M20 separate missing language/compiler/Canonical-IR planning from existing runtime and ecosystem milestones. In particular, M12 remains distributed-runtime authority, M13 offline-runtime authority, M14 media/cloud/realtime runtime and bounded provider authority, and M15 adapter-ecosystem/1.0-readiness authority. Those milestones may consume M17–M20 language contracts but must not redefine them locally. M21 extends conformance certification beyond Core only after applicable language, generator, runtime, compatibility, and editor evidence exists.

M7 remains the semantic compatibility-classification authority. Later evolution work may reconcile specified terminology and add missing evolution facts, but must project through one versioned compatibility authority rather than introducing a second classifier. M16.5 normalization candidates that alter accepted source forms are subject to the same M7 authority and must carry an explicit migration/deprecation contract before implementation.

A feature should not be described as fully supported until the applicable manifest scope and its required semantic validation, IR representation, and executable evidence justify that claim.

## Definition of Done for core features

A core language feature is considered complete when:

- [ ] syntax is documented,
- [ ] parser behavior is tested,
- [ ] semantic rules are implemented,
- [ ] invalid combinations have stable diagnostics,
- [ ] canonical IR representation is defined,
- [ ] positive and negative fixtures exist,
- [ ] generator/runtime behavior is defined if applicable,
- [ ] IDE support does not require a conflicting interpretation of the language.

For M17+ profile/language surfaces, the same discipline applies with explicit applicability: Parse/Resolve/Validate/IR evidence is required for a supported language-semantic claim; Generate, Runtime, and IDE evidence is additionally required whenever the public support statement includes those layers. A surface may remain specified, experimental, partial, or blocked without pretending every layer is applicable or complete.

## Language-surface normalization gate

Before broad M17–M20 expansion, M16.5 must disposition the measured construction hotspots from `docs/grammar-complexity-review.md` and the deterministic `tools/grammar_complexity_metrics.py` baseline. The gate covers at least colonized versus uncolonized leaves; recurring `auth`, `errors`, `retry`, `timeout`, `consistency`, and `idempotency` variants; compact versus structured forms; `profileProperty`, `uiStatement`, and `testStatement`; compound word-order mini-languages; and confusable declaration families.

A disposition may keep existing syntax, improve documentation/tooling, make contextual schemas compiler-discoverable, or nominate a compatibility-sensitive normalization candidate. It must never smuggle a syntax choice into roadmap prose. Any adopted change must be evaluated against the same model- and vendor-neutral M16 construction task corpus before and after, using semantic end-state checks and measured compile success, semantic correctness, unnecessary edits, repair loops, regressions, parse/validation success, invented syntax, wrong placement, diagnostics density, and semantic-fact recall. Results are evidence only after execution; the roadmap defines measurements, not scores.

## Recommended execution order

Existing M1–M21 milestone identities and completion states remain unchanged; M10.5 and M16.5 are additive gates and do not renumber them:

1. M9 — Release and quality baseline
2. M10 — Core conformance closure
3. M10.5 — Kotlin Compiler-Core Migration Gate
4. M11 — Production language server, with completed M11-01 through M11-04 retained and further M11-04.1/M11.5 compiler-core deepening gated by M10.5
5. M12 — Distributed runtime vertical slice
6. M13 — Offline Calendar vertical slice
7. M14 — Media, cloud, and realtime vertical slice
8. M15 — Adapter ecosystem and 1.0 readiness
9. M16 — Agent Construction and Verification
10. M16.5 — Language Surface Normalization Gate
11. M17 — Extended Type System and Standard Library
12. M18 — Advanced Backend Language
13. M19 — Frontend Language
14. M20 — Distributed, Sync, Resource, Deployment, and Evolution Language Contracts
15. M21 — Full-Language Conformance Closure

M10.5 does not move or invalidate completed M11 work. Its ordering rule is prospective: finish M10, accept the staged migration/parity architecture, then deepen M11-04.1/M11.5 compiler internals on abstractions compatible with the shared target. Scheduling may continue adapter-neutral maintenance or other explicitly dispatched work that does not deepen conflicting Python-only compiler-core architecture.

M17+ remain separate from and do not substitute for M12–M16 runtime/ecosystem ownership. Scheduling may execute prerequisites earlier when explicitly dispatched, but broad M17–M20 language-surface expansion should not bypass M16.5 normalization disposition. Roadmap identity/order and the ownership boundaries above remain stable.

Do not expand the language surface merely to advance a later milestone. Promote a capability only when its required parser, semantic, IR, fixture, runtime or explicit capability-failure, and editor boundaries can advance coherently.

The specification-to-roadmap mapping in [`spec-roadmap-gap-matrix.md`](spec-roadmap-gap-matrix.md) is a planning aid under this roadmap, not an implementation/support authority.

The next success criterion is intentionally agent-focused:

> Given an AIDL project and a change request, a model-independent coding agent can obtain bounded compiler-owned context, construct a semantic patch, validate it entirely in memory against a specific snapshot, inspect deterministic diagnostics, impact, and compatibility evidence, and apply it only while the validated preconditions still hold, without repository-wide heuristic scanning.

The next release criterion is equally concrete:

> A clean environment can install a tagged AIDL toolchain artifact, reproduce its schemas and generated output, execute every required CI gate, and run the supported Petstore workflow without modifying generated files.

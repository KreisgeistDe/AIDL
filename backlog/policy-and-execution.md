# Roadmap policy, Definition of Done, and execution order

## Implementation policy

`TODO.md` is the sole handwritten authority for roadmap order, milestone identity, and completion state. Operational execution state remains on `agents/channel`; committed legacy project `.ai/**` current-state files are not a second roadmap authority.

The project tree is intentionally `.ai/**`-free. Every project PR targeting `main` must reject any `.ai/**` endpoint, including additions, modifications, deletions, copies, and renames; the former one-time legacy deletion exceptions are obsolete because those files no longer exist in the project repository. Operational state and any maintenance of the transport workflow belong only in `KreisgeistDe/AIDL_channel@agents/channel`, never in a project PR.

`spec/conformance-manifest.json` is the separate authoritative versioned implementation/support source. New or changed support claims must update a stable manifest surface ID, use only the schema-defined status vocabulary, and carry repository-relative evidence that passes `python3 -m tools.conformance_manifest validate`. Roadmap completion alone never promotes a support claim.

The offline repository-state check `python3 -m tools.validate_repository_state` enforces the `.ai/**`-free project invariant and the roadmap, channel, and conformance authority markers. It requires no network access and runs in standard validation CI.

M10-01 records repository-level support surfaces only. M10-02 provides the exhaustive Parse/Resolve/Validate/IR/Generate/IDE matrix for every Core declaration and semantic rule; incomplete rows or evidence remain explicit in that matrix and must not be interpreted as full layer completeness. Public wording in `SUPPORT.md` is drift-checked against each manifest `supportStatement`.

The language specification is normative design input, not implementation status. Syntax or semantics documented in `docs/` remain **specified** unless conformance authority and executable evidence justify a stronger claim. Likewise, adding or completing M17+ roadmap tasks does not itself change `spec/conformance-manifest.json`, Core/profile conformance status, generator/runtime support, editor support, or release readiness.

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

Existing M1–M21 milestone identities and completion states remain unchanged; M16.5 is an additive gate and does not renumber them:

1. M9 — Release and quality baseline
2. M10 — Core conformance closure
3. M11 — Production language server
4. M12 — Distributed runtime vertical slice
5. M13 — Offline Calendar vertical slice
6. M14 — Media, cloud, and realtime vertical slice
7. M15 — Adapter ecosystem and 1.0 readiness
8. M16 — Agent Construction and Verification
9. M16.5 — Language Surface Normalization Gate
10. M17 — Extended Type System and Standard Library
11. M18 — Advanced Backend Language
12. M19 — Frontend Language
13. M20 — Distributed, Sync, Resource, Deployment, and Evolution Language Contracts
14. M21 — Full-Language Conformance Closure

M17+ remain separate from and do not substitute for M12–M16 runtime/ecosystem ownership. Scheduling may execute prerequisites earlier when explicitly dispatched, but broad M17–M20 language-surface expansion should not bypass M16.5 normalization disposition. Roadmap identity/order and the ownership boundaries above remain stable.

Do not expand the language surface merely to advance a later milestone. Promote a capability only when its required parser, semantic, IR, fixture, runtime or explicit capability-failure, and editor boundaries can advance coherently.

The specification-to-roadmap mapping in [`spec-roadmap-gap-matrix.md`](spec-roadmap-gap-matrix.md) is a planning aid under this roadmap, not an implementation/support authority.

The next success criterion is intentionally agent-focused:

> Given an AIDL project and a change request, a model-independent coding agent can obtain bounded compiler-owned context, construct a semantic patch, validate it entirely in memory against a specific snapshot, inspect deterministic diagnostics, impact, and compatibility evidence, and apply it only while the validated preconditions still hold, without repository-wide heuristic scanning.

The next release criterion is equally concrete:

> A clean environment can install a tagged AIDL toolchain artifact, reproduce its schemas and generated output, execute every required CI gate, and run the supported Petstore workflow without modifying generated files.

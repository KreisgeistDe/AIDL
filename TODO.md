# AIDL Project Roadmap

This document tracks the next implementation steps required to turn AIDL from a broad language specification into a reliable end-to-end toolchain.

The guiding principle is to finish one deterministic vertical slice before expanding the language surface further.

`roadmap/v1/` is the sole machine-readable authority for migrated milestone IDs, order, priority, status, dependencies, and terminal disposition. `TODO.md` remains the stable human entry point; for migrated milestones its status projection is deterministically checked against JSON, while linked `backlog/` files retain narrative, acceptance rationale, and milestone-specific design context. Milestones listed as `pending_migration` in `roadmap/v1/index.json` remain under their existing Markdown authority until explicitly migrated, so no milestone has overlapping independent completion authorities.

## Blocking Core Language Authority Gate

The completed design review supersedes revision-4 JSON as the future permanent semantic authority and inserts a blocking Core Language Authority Gate before any further semantics-dependent M10.5 work. The durable design and transition disposition are in `docs/core-language-authority-gate.md` and `spec/core-authority-transition-v1.json`.

- [x] **D0 — Core authority architecture review.** Select the minimal host Bootstrap Kernel plus AIDL-authored self-describing Core; reject a permanent dual-grammar model.
- [x] **I1 — Bootstrap/Core authority implementation.** Integrated as PR #89. `spec/bootstrap-kernel-v1.json`, normative `spec/core.aidl`, deterministic generated Core registry/projection, exact declaration/generic-TypeRef/modifier/body framing, focused tests, and transition disposition are on main without a project-wide authority flip.
- [x] **I2 — Core semantic model and domain migration.** Integrated as PR #90. Core-owned semantic validation, ordinary AIDL `core.domain`, deterministic diagnostics, and revision-4 compatibility normalization are on main without an authority flip.
- [x] **V1 — Independent broad Core validation.** Independently certified on the exact corrected PR #91 head and integrated on main as `f0a8097f926aa9d3940f2684c01b1d66de4dff2a`. The Core-derived semantic loader, exact projection drift checks and broad differential/compatibility boundary are accepted inputs to G1.
- [x] **G1 — Core authority integration/flip.** Independently validated and integrated as PR #92 on main at `b90c44912d7f82450c2190473035bce14bef828d`. Normative Core/Core-authored modules are now the sole permanent semantic authority; revision-4 data is compatibility/migration evidence only and production use requires the exact Core-authored compatibility binding.

After G1, `spec/language-surface-v1.json` revision 4 is no longer an independent production semantic authority. It remains frozen compatibility/migration evidence and may be consumed by legacy production normalization only after `spec/core.authority.aidl` and `spec/core.compatibility.aidl` validate and authorize its exact Git-blob identity. PR #88's Kotlin type-construction implementation remains bounded evidence; semantics-dependent Kotlin adaptation resumes only through the separately gated M10.5 sequence.

## M10.1 blocking language-freeze gate

[M10.1 — Normative Language Surface Freeze Gate](backlog/m10-1-language-freeze.md) is the historical revision-4 language-design gate sequenced after completed M10 Core conformance. Its JSON contract and certifications remain compatibility/migration evidence during the Core authority transition; they must not evolve into a second permanent normative grammar.

Stable M10.1 work packages are numbered independently of PRs. Completed packages stay checked only while the repository continues to contain the required revision-4 compatibility contract, production bridge and regression evidence.

- [x] **M10.1-01 — Freeze the canonical language-surface contract.** `docs/m10-1-language-surface-freeze.md` and `spec/language-surface-v1.json` remain the frozen revision-4 compatibility target during the Core transition.
- [x] **M10.1-02 — Establish the executable legacy-to-canonical compatibility bridge.** Legacy source facts normalize through the contract-owned bridge with deterministic semantic hashes and explicit migration separation.
- [x] **M10.1-03 — Integrate canonical normalization into the production compiler path.** Production normalization consumes real compiler analysis and fails closed outside its lossless semantic envelope.
- [x] **M10.1-04 — Close operation signatures and baseline body parity.** Typed query/mutation parameters, reference projections, defaults and scalar body facts have production parity.
- [x] **M10.1-05 — Close structured operation error parity.** Ordered query/mutation `errors` semantics are contract-backed and admitted only from complete compiler-owned evidence.
- [x] **M10.1-06 — Close structured operation policy semantics.** Frozen-v1 `allow` supplies contract-owned authorize Production-Parity. `auth`, `cache` and `consistency` have explicit contract-derived exclusion dispositions because revision 4 declares no such BodySlots; their legacy source facts continue to fail closed. PR #67/#68 remain auth evidence prerequisites only and do not broaden the frozen contract.
- [x] **M10.1-07 — Close operation execution semantics.** Frozen-v1 `TypeRef.range` and operation-parameter `default` modifiers have contract-owned Production-Parity. Generic TypeRef arguments, non-range constraints, operation generics, and mutation `idempotency`/`transaction` remain explicit contract-derived fail-closed exclusions (`AIDL-N015`/`AIDL-N010` into existing `AIDL-N013` production losslessness gating); no new execution syntax or runtime meaning is introduced.
- [x] **M10.1-08 — Close declaration-family production parity.** Frozen-v1's 48 canonical semantic declaration kinds now have deterministic contract-derived dispositions from the existing Production Normalization gates: ten are admitted with production parity and the remaining 38 are explicitly non-admitted/fail-closed; no parser/runtime/schema semantics are widened.
- [x] **M10.1-09 — Add complete language-surface coverage and differential conformance.** Contract leaves, declaration/modifier dispositions and TypeRef/reference-projection shapes are audited from frozen-v1 plus existing compiler-owned evidence; differential regressions prove stable legacy/canonical semantics and fail-closed unsupported shapes without widening revision 4.
- [x] **M10.1-10 — Certify M10.1 closure and unblock bounded differential implementation.** `tools/compiler_language_surface_certification.py` certifies the complete revision-4 Production Semantic Envelope with no unresolved language decision. After G1 this certification remains compatibility evidence only; it cannot override Core-owned semantic authority.

M10.1 acceptance remains certified by `docs/m10-1-closure-certification.md` for the revision-4 compatibility envelope: all frozen-v1 semantics are lossless or deterministically fail-closed; equivalent legacy/canonical representations converge on stable semantics/hashes; Production Normalization remains contract-derived without parallel grammars or semantic tables; formatter and migration remain separate; query/mutation and declaration-family dispositions are complete; coverage/differential drift is deterministic in CI; and the frozen model remains available as migration evidence.

## M10.2 canonical language documentation/source migration gate

[M10.2 — Canonical Language Documentation & Source Migration Gate](backlog/m10-2-m10-3-language-example-migration.md) consumes completed M10.1 before any final Kotlin parity baseline is frozen. It remains revision-4 documentation/source inventory and migration evidence; it does not override the blocking Core authority gate.

- [x] **M10.2-01 — Classify and migrate the canonical language documentation and committed source surface.** **P1** `spec/m10-2-language-surface-classification.json` and `tools/m10_2_language_surface_classification.py` exhaustively classify committed `.aidl` source plus discovered AIDL/EBNF documentation surfaces, fail closed on classification/contract drift, align the revision-4 grammar evidence, and leave executable reference-source migration to M10.3 without semantic widening.

## M10.3 reference-example and production semantic closure gate

[M10.3 — Reference Example & Production Semantic Closure Gate](backlog/m10-2-m10-3-language-example-migration.md) depends on completed M10.2. It remains revision-4 reference-example and production-semantic evidence during the Core transition.

- [x] **M10.3-01 — Migrate intended reference examples and close production semantic mismatches.** **P1** `spec/m10-3-closure-certification.json` and `tools/m10_3_closure_certification.py` compose the exhaustive M10.2 classification, the complete shared disposition, all three integrated reference-app inventories, and all committed valid/compatibility, rejection and semantic-diagnostic fixture classes. New unclassified/inconsistent app or fixture surfaces fail closed. `app.links` remains separately versioned-admission only; all other retained mismatches remain explicit non-production/fail-closed evidence; revision 4, Production Normalization, Canonical IR meaning and parser/compiler/runtime semantics are unchanged.

The former execution order `M10.1 -> M10.2 -> M10.3 -> M10.5` was interrupted by the Core gate. D0, I1, I2, V1 and G1 are now complete, so the next dependency-ready step is the refreshed M10.5-01 parity-baseline gate. Existing language-neutral parity harness/infrastructure may remain as evidence, but future semantic work must remain governed by Core.

## M10.5 Kotlin compiler-core migration gate

[M10.5 — Kotlin Compiler-Core Migration Gate](backlog/m10-5-kotlin-compiler-migration.md) is now unblocked by the completed Core gate, but its internal sequencing remains mandatory. M10.5-01 must be refreshed and independently accepted before M10.5-02 or later Kotlin semantic work may proceed. Python and revision-4 artifacts remain compatibility/conformance evidence under Core-owned authority.

- [ ] **M10.5-01 — Refresh the Python parity baseline and differential harness.** **Next dependency-ready gate.** PR #77 is the focused candidate historical/provisional parity evidence and is already merged on main via `1574963eed95a2f80c1cdc47f48a3eaa39df4a4b`; it is not a future integration target. Completion requires fresh independent validation and integration of a separate post-G1 current-main refresh/revalidation package reconciled with the Core-owned authority and current Python reference state; Gate 01 is not complete in this reconciliation.
- [ ] **M10.5-02 and later Kotlin work.** Blocked until M10.5-01 is durably integrated. PR #88's integrated TypeConstruction slice remains bounded historical evidence; generic Core TypeRef adaptation and further semantics-dependent Kotlin work belong only after Gate 01.

## Priority legend

- **P0** — required for the first usable end-to-end AIDL workflow
- **P1** — required for a credible developer experience and CI usage
- **P2** — ecosystem and productivity improvements after the core is stable

## Roadmap sections

1. [M1–M3 — Language, semantics, canonical IR, and CLI](backlog/m1-m3-foundations.md)
2. [M4–M8 — Vertical slice, fixtures, IDE, compatibility, and agent tooling](backlog/m4-m8-tooling.md)
3. [M9–M10 — Release baseline and Core conformance](backlog/m9-m10-release-conformance.md)
4. [Core Language Authority Gate](docs/core-language-authority-gate.md)
5. [M10.1 — Normative Language Surface Freeze Gate](backlog/m10-1-language-freeze.md)
6. [M10.2–M10.3 — Pre-Kotlin language and example migration gates](backlog/m10-2-m10-3-language-example-migration.md)
7. [M10.5 — Kotlin Compiler-Core Migration Gate](backlog/m10-5-kotlin-compiler-migration.md)
8. [M11 — Production language server and compiler service](backlog/m11-compiler-service.md)
9. [M12–M14 — Runtime vertical slices](backlog/m12-m14-runtime-vertical-slices.md)
10. [M15–M16 — Ecosystem readiness and agent construction](backlog/m15-m16-ecosystem-agents.md)
11. [M16.5 — Language Surface Normalization Gate](backlog/m16-5-language-surface-normalization.md)
12. [M17–M21 — Full specified-language coverage](backlog/m17-m21-full-language-coverage.md)
13. [Specification-to-roadmap gap matrix](backlog/spec-roadmap-gap-matrix.md)
14. [Roadmap policy, Definition of Done, and recommended execution order](backlog/policy-and-execution.md)

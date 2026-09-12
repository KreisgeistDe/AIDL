# AIDL Project Roadmap

This document tracks the next implementation steps required to turn AIDL from a broad language specification into a reliable end-to-end toolchain.

The guiding principle is to finish one deterministic vertical slice before expanding the language surface further.

`roadmap/v1/` is the sole machine-readable authority for migrated milestone IDs, order, priority, status, dependencies, and terminal disposition. `TODO.md` remains the stable human entry point; for migrated milestones its status projection is deterministically checked against JSON, while linked `backlog/` files retain narrative, acceptance rationale, and milestone-specific design context. Milestones listed as `pending_migration` in `roadmap/v1/index.json` remain under their existing Markdown authority until explicitly migrated, so no milestone has overlapping independent completion authorities.

## M10.1 blocking language-freeze gate

[M10.1 — Normative Language Surface Freeze Gate](backlog/m10-1-language-freeze.md) is the language-design authority sequenced after completed M10 Core conformance and before the pre-Kotlin M10.2/M10.3 gates. Existing legacy syntax remains accepted until an explicit versioned parser/migrator implementation; there is no permanent parallel grammar.

Stable M10.1 work packages are numbered independently of PRs. Completed packages stay checked only while the repository continues to contain the required normative contract, production bridge and regression evidence.

- [x] **M10.1-01 — Freeze the canonical language-surface contract.** `docs/m10-1-language-surface-freeze.md` and `spec/language-surface-v1.json` remain the normative frozen-v1 target.
- [x] **M10.1-02 — Establish the executable legacy-to-canonical compatibility bridge.** Legacy source facts normalize through the contract-owned bridge with deterministic semantic hashes and explicit migration separation.
- [x] **M10.1-03 — Integrate canonical normalization into the production compiler path.** Production normalization consumes real compiler analysis and fails closed outside its lossless semantic envelope.
- [x] **M10.1-04 — Close operation signatures and baseline body parity.** Typed query/mutation parameters, reference projections, defaults and scalar body facts have production parity.
- [x] **M10.1-05 — Close structured operation error parity.** Ordered query/mutation `errors` semantics are contract-backed and admitted only from complete compiler-owned evidence.
- [x] **M10.1-06 — Close structured operation policy semantics.** Frozen-v1 `allow` supplies contract-owned authorize Production-Parity. `auth`, `cache` and `consistency` have explicit contract-derived exclusion dispositions because revision 4 declares no such BodySlots; their legacy source facts continue to fail closed. PR #67/#68 remain auth evidence prerequisites only and do not broaden the frozen contract.
- [x] **M10.1-07 — Close operation execution semantics.** Frozen-v1 `TypeRef.range` and operation-parameter `default` modifiers have contract-owned Production-Parity. Generic TypeRef arguments, non-range constraints, operation generics, and mutation `idempotency`/`transaction` remain explicit contract-derived fail-closed exclusions (`AIDL-N015`/`AIDL-N010` into existing `AIDL-N013` production losslessness gating); no new execution syntax or runtime meaning is introduced.
- [x] **M10.1-08 — Close declaration-family production parity.** Frozen-v1's 48 canonical semantic declaration kinds now have deterministic contract-derived dispositions from the existing Production Normalization gates: ten are admitted with production parity and the remaining 38 are explicitly non-admitted/fail-closed; no parser/runtime/schema semantics are widened.
- [x] **M10.1-09 — Add complete language-surface coverage and differential conformance.** Contract leaves, declaration/modifier dispositions and TypeRef/reference-projection shapes are audited from frozen-v1 plus existing compiler-owned evidence; differential regressions prove stable legacy/canonical semantics and fail-closed unsupported shapes without widening revision 4.
- [x] **M10.1-10 — Certify M10.1 closure and unblock bounded differential implementation.** `tools/compiler_language_surface_certification.py` certifies the complete revision-4 Production Semantic Envelope with no unresolved language decision. This certification remains semantic authority, but M10.5 migration work is now sequenced behind M10.2/M10.3 source/documentation/example readiness gates.

M10.1 acceptance is certified by `docs/m10-1-closure-certification.md`: all frozen-v1 semantics are lossless or deterministically fail-closed; equivalent legacy/canonical representations converge on stable semantics/hashes; Production Normalization remains contract-derived without parallel grammars or semantic tables; formatter and migration remain separate; query/mutation and declaration-family dispositions are complete; coverage/differential drift is deterministic in CI; and the frozen model can be implemented cross-language without inventing a language decision.

## M10.2 canonical language documentation/source migration gate

[M10.2 — Canonical Language Documentation & Source Migration Gate](backlog/m10-2-m10-3-language-example-migration.md) consumes completed M10.1 before any final Kotlin parity baseline is frozen. It is a documentation/source inventory and migration gate, not a semantic-widening implementation.

- [x] **M10.2-01 — Classify and migrate the canonical language documentation and committed source surface.** **P1** `spec/m10-2-language-surface-classification.json` and `tools/m10_2_language_surface_classification.py` exhaustively classify committed `.aidl` source plus discovered AIDL/EBNF documentation surfaces, fail closed on classification/contract drift, align the normative grammar to frozen revision 4, and leave executable reference-source migration to M10.3 without semantic widening.

## M10.3 reference-example and production semantic closure gate

[M10.3 — Reference Example & Production Semantic Closure Gate](backlog/m10-2-m10-3-language-example-migration.md) depends on completed M10.2. It migrates intended reference examples to the unified target grammar and resolves every M10.2 mismatch explicitly before M10.5 becomes eligible for a final parity baseline.

- [ ] **M10.3-01 — Migrate intended reference examples and close production semantic mismatches.** **P1** Preserve explicit negative and compatibility fixture classifications, align diagnostics/semantics/example explanations, add deterministic grammar-to-examples conformance checks, and require any actual Python reference semantic/admission change to use an explicit versioned contract update, re-freeze, exhaustive coverage, and certification rather than implicit widening.

The required execution order is `M10.1 -> M10.2 -> M10.3 -> refreshed M10.5-01 -> M10.5-02 and later Kotlin work`. Current PR #77 and any other pre-M10.2 M10.5-01 baseline are provisional/deferred and cannot serve as the final Kotlin parity baseline. M16.5 remains the later broader normalization/metamodel milestone and does not substitute for M10.2/M10.3.

## Priority legend

- **P0** — required for the first usable end-to-end AIDL workflow
- **P1** — required for a credible developer experience and CI usage
- **P2** — ecosystem and productivity improvements after the core is stable

## Roadmap sections

1. [M1–M3 — Language, semantics, canonical IR, and CLI](backlog/m1-m3-foundations.md)
2. [M4–M8 — Vertical slice, fixtures, IDE, compatibility, and agent tooling](backlog/m4-m8-tooling.md)
3. [M9–M10 — Release baseline and Core conformance](backlog/m9-m10-release-conformance.md)
4. [M10.1 — Normative Language Surface Freeze Gate](backlog/m10-1-language-freeze.md)
5. [M10.2–M10.3 — Pre-Kotlin language and example migration gates](backlog/m10-2-m10-3-language-example-migration.md)
6. [M10.5 — Kotlin Compiler-Core Migration Gate](backlog/m10-5-kotlin-compiler-migration.md)
7. [M11 — Production language server and compiler service](backlog/m11-compiler-service.md)
8. [M12–M14 — Runtime vertical slices](backlog/m12-m14-runtime-vertical-slices.md)
9. [M15–M16 — Ecosystem readiness and agent construction](backlog/m15-m16-ecosystem-agents.md)
10. [M16.5 — Language Surface Normalization Gate](backlog/m16-5-language-surface-normalization.md)
11. [M17–M21 — Full specified-language coverage](backlog/m17-m21-full-language-coverage.md)
12. [Specification-to-roadmap gap matrix](backlog/spec-roadmap-gap-matrix.md)
13. [Roadmap policy, Definition of Done, and recommended execution order](backlog/policy-and-execution.md)

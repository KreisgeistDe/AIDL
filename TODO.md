# AIDL Project Roadmap

This document tracks the next implementation steps required to turn AIDL from a broad language specification into a reliable end-to-end toolchain.

The guiding principle is to finish one deterministic vertical slice before expanding the language surface further.

`roadmap/v1/` is the sole machine-readable authority for migrated milestone IDs, order, priority, status, dependencies, and terminal disposition. `TODO.md` remains the stable human entry point; for migrated milestones its status projection is deterministically checked against JSON, while linked `backlog/` files retain narrative, acceptance rationale, and milestone-specific design context. Milestones listed as `pending_migration` in `roadmap/v1/index.json` remain under their existing Markdown authority until explicitly migrated, so no milestone has overlapping independent completion authorities.

## M10.1 blocking language-freeze gate

[M10.1 — Normative Language Surface Freeze Gate](backlog/m10-1-language-freeze.md) is the language-design authority sequenced after completed M10 Core conformance and before M10.5. It must be reviewed before M10.5-03 front-end/IR migration and before further M16.5 syntax adoption. M10.5-01/-02 work that is genuinely migration-neutral may continue independently where the M10.5 roadmap permits it. Existing legacy syntax remains accepted until an explicit versioned parser/migrator implementation; there is no permanent parallel grammar.

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
- [x] **M10.1-10 — Certify M10.1 closure and unblock M10.5-03.** `tools/compiler_language_surface_certification.py` certifies the complete revision-4 Production Semantic Envelope from the integrated M10.1 evidence, with no unresolved language decision remaining for M10.5-03. The unblock is bounded to differential implementation of the frozen model and does not authorize semantic widening.

M10.1 acceptance is certified by `docs/m10-1-closure-certification.md`: all frozen-v1 semantics are lossless or deterministically fail-closed; equivalent legacy/canonical representations converge on stable semantics/hashes; Production Normalization remains contract-derived without parallel grammars or semantic tables; formatter and migration remain separate; query/mutation and declaration-family dispositions are complete; coverage/differential drift is deterministic in CI; and M10.5-03 can implement revision 4 without inventing a language decision.

## M10.5 Kotlin compiler-core migration gate

[M10.5 — Kotlin Compiler-Core Migration Gate](backlog/m10-5-kotlin-compiler-migration.md) keeps Python authoritative while migration evidence and later Kotlin slices are introduced incrementally.

- [x] **M10.5-01 — Freeze the Python reference contract and differential harness boundary.** `tools/m10_5_reference_contract.json` and `tools/m10_5_reference_contract.py` inventory existing compiler/IR/CLI/query/fixture/CI evidence, fingerprint it deterministically, and fail closed on contract or comparison drift without becoming a second language authority.
- [ ] **M10.5-02 — Establish the Kotlin Multiplatform compiler skeleton.** Keep semantic authority in Python while defining common/Native/JVM module boundaries and coverage gates.
- [ ] **M10.5-03 — Begin bounded front-end parity slices.** Migrate only against frozen-v1 revision 4 with Python-versus-Kotlin differential evidence.

Later M10.5 phases remain governed by the backlog and are not implied complete by M10.5-01.

## Priority legend

- **P0** — required for the first usable end-to-end AIDL workflow
- **P1** — required for a credible developer experience and CI usage
- **P2** — ecosystem and productivity improvements after the core is stable

## Roadmap sections

1. [M1–M3 — Language, semantics, canonical IR, and CLI](backlog/m1-m3-foundations.md)
2. [M4–M8 — Vertical slice, fixtures, IDE, compatibility, and agent tooling](backlog/m4-m8-tooling.md)
3. [M9–M10 — Release baseline and Core conformance](backlog/m9-m10-release-conformance.md)
4. [M10.1 — Normative Language Surface Freeze Gate](backlog/m10-1-language-freeze.md)
5. [M10.5 — Kotlin Compiler-Core Migration Gate](backlog/m10-5-kotlin-compiler-migration.md)
6. [M11 — Production language server and compiler service](backlog/m11-compiler-service.md)
7. [M12–M14 — Runtime vertical slices](backlog/m12-m14-runtime-vertical-slices.md)
8. [M15–M16 — Ecosystem readiness and agent construction](backlog/m15-m16-ecosystem-agents.md)
9. [M16.5 — Language Surface Normalization Gate](backlog/m16-5-language-surface-normalization.md)
10. [M17–M21 — Full specified-language coverage](backlog/m17-m21-full-language-coverage.md)
11. [Specification-to-roadmap gap matrix](backlog/spec-roadmap-gap-matrix.md)
12. [Roadmap policy, Definition of Done, and recommended execution order](backlog/policy-and-execution.md)

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
- [ ] **M10.1-08 — Close declaration-family production parity.** Every remaining frozen-v1 declaration family receives an explicit disposition: production-parity, intentionally excluded or not applicable.
- [ ] **M10.1-09 — Add complete language-surface coverage and differential conformance.** Maintain a complete machine-readable inventory/disposition, differential evidence and deterministic CI drift protection.
- [ ] **M10.1-10 — Certify M10.1 closure and unblock M10.5-03.** Complete the final audit, regression set and Production Semantic Envelope certification with no unresolved language decision required by M10.5-03.

M10.1 acceptance requires all frozen-v1 semantics to be lossless or deterministically fail-closed; equivalent legacy/canonical representations to converge on identical semantics and hashes; Production Normalization to derive only from the frozen contract plus compiler-owned evidence without parallel grammars or semantic tables; formatter and migration behavior to remain separate; query/mutation and required declaration families to have complete parity or explicit exclusion; coverage/compatibility drift to be deterministic in CI; and M10.5-03 to be implementable without inventing an unresolved language decision.

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

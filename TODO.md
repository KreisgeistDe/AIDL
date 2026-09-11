# AIDL Project Roadmap

This document tracks the next implementation steps required to turn AIDL from a broad language specification into a reliable end-to-end toolchain.

The guiding principle is to finish one deterministic vertical slice before expanding the language surface further.

`TODO.md` remains the roadmap authority and stable entry point. The linked files under `backlog/` are constituent sections of this roadmap, not independent roadmap authorities; they preserve milestone identity, order, checkbox/completion state, acceptance criteria, policy, Definition of Done, and execution order. The relative links below intentionally remain valid if this index is later renamed to `BACKLOG.md`.

## M10.1 blocking language-freeze gate

[M10.1 — Normative Language Surface Freeze Gate](backlog/m10-1-language-freeze.md) is the language-design authority sequenced after completed M10 Core conformance and before M10.5. It must be reviewed before M10.5-03 front-end/IR migration and before further M16.5 syntax adoption. M10.5-01/-02 work that is genuinely migration-neutral may continue independently where the M10.5 roadmap permits it. Existing legacy syntax remains accepted until an explicit versioned parser/migrator implementation; there is no permanent parallel grammar.

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

# Maintenance — Project Recovery Roadmap

Status: active maintenance recovery plan.

This document records the project-recovery sequence derived from the SpecialTask and roadmap audit performed against the current repository state. It is **not** a second roadmap authority. `roadmap/v1/` remains the sole machine-readable authority for migrated milestones, while milestones still marked `pending_migration` continue to use their existing Markdown authority until migrated. The purpose of this maintenance plan is to remove that split authority and reconcile the language-design authority chain before further broad semantic work.

## Recovery goals

1. Finish the machine-readable roadmap migration so current and future work can be selected deterministically.
2. Reconcile historical language-design initiatives so only the current Core-owned language authority can govern future implementation.
3. Remove stale blocking authority from superseded planning gates without deleting useful historical evidence.
4. Restore a thin orchestration model in which workflow state, roadmap state, and the previous agent handoff can be consumed without broad repository reinterpretation.
5. Only after authority recovery, complete the end-to-end projection of the self-described Core language into grammar, examples, fixtures, tooling, and later compiler parity work.

## Audit summary

### Machine-readable roadmap

The machine-readable roadmap initiative is technically present and validated, but its rollout is incomplete. `roadmap/v1/index.json` currently treats M10, M10.1, M10.2, and M10.3 as authoritative JSON milestones. M10.5, M11-M21, and M16.5 remain `pending_migration` and therefore still depend on Markdown authority.

Disposition: **partial — finish rollout, do not redesign from scratch.**

### Revision-4 language freeze and migration

The earlier language-design sequence produced the M10.1 revision-4 language freeze followed by M10.2 documentation/source classification and M10.3 reference-example closure. Those packages remain valuable compatibility, migration, and conformance evidence, but they are no longer the permanent semantic language authority after the later Core authority transition.

Disposition: **complete in historical scope; compatibility evidence only for future authority decisions.**

### Self-describing Core authority

The later Core Language Authority Gate selected a minimal Bootstrap Kernel plus AIDL-authored self-describing Core, completed D0/I1/I2/V1/G1, and subsequently integrated the binding self-description correction. Current project intent is that direct Core/Core-authored modules are the sole permanent semantic authority, with generated meta-IR non-authoritative and revision-4 artifacts retained only as compatibility/migration evidence.

Disposition: **current normative direction; preserve and complete public-surface rollout.**

### M16.5 language-surface normalization

M16.5 was created as an evidence and decision gate before later language-authority corrections. Its design, compatibility, prototype, and evaluation material remains useful historical evidence, but its old rule that no production syntax change is authorized until a later E9 proposal must not override a subsequently accepted Core authority decision.

Disposition: **historical evidence; superseded as a blocking authority wherever it conflicts with the accepted Core authority chain.**

## Ordered maintenance recovery packages

### R1 — Complete roadmap/v1 migration

Priority: P0

Goal: make the current project roadmap deterministically queryable without requiring the orchestrator to reinterpret TODO/backlog prose.

Work:

- Extend `roadmap/v1/` to cover all current milestone authorities, at minimum M10.5 through M21 and M16.5.
- Preserve existing milestone/work-package IDs, status, order, priority, dependencies, evidence, references, and terminal dispositions conservatively.
- Add any schema support needed for explicit authority/supersession relationships instead of encoding them only in prose.
- Keep `blocked` derived from status plus dependency graph rather than as a second hand-maintained truth.
- Update `tools/roadmap.py` and tests only where required to query the completed graph deterministically.
- Bind TODO/backlog status projections to the JSON authority with deterministic drift checks.

Acceptance:

- Every active milestone is represented in `roadmap/v1` or is intentionally and explicitly excluded with a documented terminal disposition.
- `python3 tools/roadmap.py validate` succeeds on the complete current graph.
- `python3 tools/roadmap.py next` identifies the actual dependency-ready current work, including the active M10.5 sequence.
- Unknown IDs, cycles, duplicate IDs/order, invalid supersession, and Markdown/JSON status drift fail deterministically.
- No project semantics, parser behavior, runtime behavior, or compiler behavior changes as part of this package.

### R2 — Reconcile the language-authority chain

Priority: P0

Depends on: R1

Goal: make the current accepted language authority unambiguous across roadmap, specification, grammar, and historical design gates.

Required authority chain:

1. revision-4 M10.1/M10.2/M10.3 artifacts remain historical compatibility/migration/conformance evidence;
2. the accepted Core Language Authority Gate and its binding self-description correction govern current semantic authority;
3. M16.5 remains historical design/evaluation evidence and does not independently block a later accepted Core authority decision;
4. generated projections/meta-IR remain derived, not independent language authority.

Work:

- Record explicit `supersedes` / `superseded_by` or equivalent machine-readable relationships in the roadmap/authority model.
- Correct stale authority claims in durable project documentation, especially any statement that still presents revision-4 `spec/language-surface-v1.json` as the current semantic authority.
- Preserve revision-4 material where needed for compatibility and regression evidence rather than deleting it.
- Ensure M16.5 documents clearly distinguish historical design gates from current blocking authority.

Acceptance:

- No durable project document claims that revision 4 and direct Core are simultaneous permanent semantic authorities.
- Current authority can be determined without interpreting chronological SpecialTask history.
- Historical compatibility and evaluation evidence remains available and referenced.
- CI/repository-state validation detects contradictory authority markers where practical.

### R3 — Add a deterministic roadmap context projection for agents

Priority: P1

Depends on: R1, R2

Goal: give orchestrators and executors a compact read-only view of the relevant project roadmap state, analogous to the existing Channel LLM workflow projections.

Work:

- Extend `tools/roadmap.py` or add a small read-only wrapper with a stable JSON mode for one current item/initiative.
- Include direct dependencies, transitive blockers, next dependency-ready candidates, authority/supersession information, remaining acceptance criteria, and evidence/reference paths.
- Do not make strategic language decisions inside the tool; project decisions must already be represented in authoritative data.
- Keep output deterministic, bounded, offline, and suitable for LLM consumption.

Acceptance:

- An orchestrator can obtain current roadmap context without rereading all of TODO/backlog.
- The projection never invents state not present in authoritative roadmap data.
- Stable tests cover ready, blocked, superseded, terminal, and ambiguous/invalid graph cases.

### R4 — Restore thin orchestration semantics

Priority: P1

Depends on: R3

Goal: return the orchestrator to routing and bounded decision-making rather than broad project-state reconstruction.

Normal decision inputs should be:

- current Channel `orchestrator-context` / admission state;
- current roadmap context / next dependency-ready work;
- the previous validated result and its `next_task` where present;
- an explicit active SpecialTask/initiative only when it intentionally overrides ordinary roadmap sequencing.

Rules:

- Prefer an explicit valid `next_task` from the previous result when it is still consistent with current authoritative roadmap/project state.
- Use roadmap dependency order as the ordinary fallback.
- Escalate to broad architecture/planning analysis only when the handoff is absent, blocked, contradictory, or an active SpecialTask intentionally changes direction.
- A newer accepted initiative must explicitly supersede conflicting older gates rather than silently coexist with them.

Acceptance:

- Routine completed work can advance to its next package without a full repository-wide planning pass.
- SpecialTask-driven direction changes leave durable authority/supersession state in the project.
- Workflow safety checks remain deterministic and separate from semantic project decisions.

### R5 — Complete the self-described Core public-language rollout

Priority: P1

Depends on: R1-R4

Goal: finish the already-accepted Core architecture end-to-end instead of starting another competing language-design initiative.

Work:

- Treat the current self-described Core and Bootstrap boundary as the starting authority.
- Reconcile normative grammar documentation with that authority.
- Migrate positive examples, reference applications, and fixtures to the intended current language surface or explicitly classify them as compatibility/rejection/historical evidence.
- Align parser/AST/IR/resolver/type-checking/diagnostics/formatter/IDE surfaces only as required by the accepted Core language contract.
- Add deterministic drift/conformance checks between Core authority, grammar projection, examples, and implementation behavior.
- Preserve revision-4 compatibility paths only where explicitly required; do not restore it as parallel permanent semantic authority.

Acceptance:

- `docs/06-grammar.md` is a projection of the current Core-owned language rather than an independent revision-4 authority.
- Representative Core declaration kinds and their examples are accepted end-to-end by the intended implementation path.
- Positive examples no longer teach a syntax that conflicts with current Core authority.
- Historical/compatibility syntax is explicitly classified and tested as such.
- No unresolved permanent dual-authority language model remains.

### R6 — Resume ordinary milestone execution

Priority: P1

Depends on: R5

Goal: return to normal roadmap-driven product development.

Work:

- Recompute the next dependency-ready work from the complete machine-readable roadmap.
- Resume M10.5 and later milestones only against the reconciled language authority.
- Continue to require focused implementation, independent validation where applicable, unchanged-head integration, and deterministic CI.

Acceptance:

- Project progression is again determined by machine-readable roadmap state plus explicit active initiatives, not historical conversation or SpecialTask reconstruction.
- Future SpecialTasks either complete their rollout or leave an explicit supersession/follow-up package in the roadmap before they are considered closed.

## Maintenance invariants

- Do not create another independent roadmap or language authority.
- Do not discard useful historical evidence merely because its authority role changed.
- Do not let a planning/evaluation gate silently override a later accepted architecture decision.
- Every direction-changing initiative must explicitly record what it supersedes.
- Every partially migrated authority must have an explicit remaining migration package.
- Prefer deterministic read-only tooling over repeated LLM reconstruction of repository state.
- New workflow rules should replace obsolete complexity rather than merely accumulate beside it.

## Immediate next action

Execute **R1 — Complete roadmap/v1 migration** as the next maintenance package. Do not begin another broad language redesign before R1 and R2 establish one machine-readable roadmap and one unambiguous language-authority chain.

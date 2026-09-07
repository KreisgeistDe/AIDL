# M15–M16 — Ecosystem readiness and agent construction

## Milestone M15 — Adapter Ecosystem and 1.0 Readiness

Goal: establish the published compatibility, security, and operational evidence required for a stable AIDL ecosystem.

- [ ] **P1** Publish versioned language, profile, canonical IR, CLI, adapter, generated-manifest, and wire-schema contracts.
- [ ] **P1** Define an adapter SDK and executable conformance suite for resources, delivery, deployment, and failure behavior.
- [ ] **P1** Require two independently implemented cloud adapters to pass the same conformance suite.
- [ ] **P1** Test old clients, APIs, events, persisted schemas, and rolling deployments across supported compatibility windows.
- [ ] **P1** Validate expand/backfill/contract migrations, rollback behavior, projection replay, and disaster recovery end to end.
- [ ] **P1** Complete external security, privacy, threat-model, dependency, and generated-code reviews.
- [ ] **P2** Publish support lifecycles, deprecation policy, reproducible benchmarks, examples, and migration guides.
- [ ] **P1** Define and satisfy the final language/toolchain 1.0 release criteria without conflating independently versioned profiles and adapters.

### M15 acceptance criteria

- [ ] Published compatibility contracts are stable, independently versioned, and backed by executable conformance evidence.
- [ ] Two cloud adapters pass the same application, failure, migration, and rolling-upgrade suites.
- [ ] External security and privacy findings are resolved or documented with explicit release decisions.
- [ ] A 1.0 release can be reproduced from source and upgraded from every supported pre-1.0 compatibility baseline.

## Milestone M16 — Agent Construction and Verification

Goal: enable model-independent coding agents to construct and change AIDL projects through compiler-authoritative, transactional and verifiable operations.

M16 builds on M7 as the compatibility authority, M8 as the bounded read/query-tooling baseline, and M11 as the snapshot/service/transport foundation. It does not redefine runtime or ecosystem responsibilities owned by M12–M15.

- [ ] **P1** Add compiler-authoritative in-memory semantic patch validation and atomic apply with snapshot preconditions, diagnostics, impact, compatibility, and rollback.
- [ ] **P1** Add an in-memory `validate-change` operation that applies a proposed change only to a specific compiler snapshot and returns `check`, impact, semantic diff, M7 compatibility classification, and applicable plan evidence without modifying project files.
- [ ] **P1** Add versioned compiler-owned construction capabilities that report legal declaration kinds for a location, required clauses, admissible field types, and compiler-authorized fixes without reconstructing semantics from agent prompts, skills, or heuristics.
- [ ] **P1/P2** Add a model-independent Natural-Language-to-AIDL evaluation suite with roughly 50–100 representative construction/change tasks and metrics for compile success, semantic correctness, unnecessary edits, repair loops, and regressions.
- [ ] **P1** Add versioned semantic agent-task fixtures containing an initial project, user requirement, and acceptable semantic end-state or invariants; validate compiler/IR properties rather than exact text diffs so multiple correct implementations can pass.
- [ ] **P2** Add an explicit bounded-context construction API on top of M8 where an agent supplies a token/element budget and task focus and the compiler returns the smallest semantically closed context needed for the change, with deterministic bounds, totals, ordering, and truncation metadata.
- [ ] **P1** Add factual edit provenance and machine audit evidence containing the source semantic hash, compiler version, proposed/applied patch, result hash, before/after diagnostics, M7 compatibility class, and executed tests without storing model chain-of-thought or other hidden reasoning.
- [ ] **P1** Define compiler/policy-owned authorization boundaries for agent edits using M7 compatibility classes and explicit policy evidence to distinguish changes eligible for automatic apply from changes requiring human approval, such as public API breaks or schema migrations.
- [ ] **P2** Add structured remediation plans that order dependent repair steps beyond individual fixes, while reusing compiler diagnostics and M7 migration/compatibility evidence instead of introducing a second compatibility engine.
- [ ] **P2** Define a versioned model- and vendor-neutral agent operation protocol for compiler-owned construction and verification capabilities; CLI, LSP, MCP, or future transports may project the protocol but must not own language semantics.
- [ ] **P1** Enforce stale-agent and concurrent-edit protection so patch validation/apply is bound to exact source/semantic hashes and snapshot preconditions and fails deterministically when a human or another agent has advanced project state.
- [ ] **P1/P2** Add adversarial agent-security regressions proving comments, documentation, or AIDL strings cannot bypass compiler rules, path boundaries remain enforced, generated files cannot be manipulated outside authorized ownership flows, and compatibility/compiler disagreement can never be relabeled as safe by an agent.

### M16 acceptance criteria

- [ ] An agent can validate a complete change against an in-memory snapshot without modifying project files.
- [ ] An accepted semantic patch can be applied only against the snapshot against which it was validated.
- [ ] Every change returns deterministic before/after hashes, diagnostics, impact, and compatibility evidence.
- [ ] Representative natural-language tasks can be solved without repository-wide heuristic scanning.
- [ ] Agent benchmarks measure semantic correctness rather than identical text output.

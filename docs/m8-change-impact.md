# M8 — Compiler-authoritative change impact

`aidl impact <FQN> [PATH ...]` projects a bounded impact view for one exactly resolvable declaration or operation. It is a read-only agent-context command over facts that already exist in compiler analysis and Canonical IR.

## Evidence boundary

The command does not scan source text, inspect generated files, or invent dependency semantics. The selected FQN is resolved through the existing compiler inspection boundary. Directly affected declarations are only Canonical-IR declarations whose already-materialized node contains the selected stable `declarationId`.

Public-contract evidence is limited to declarations already materialized on Canonical-IR API/topic surfaces: exposed APIs, operations listed by those APIs, activated topics, and event IDs listed by those topics. Persisted-state evidence is limited to impacted Canonical-IR `entity` declarations.

The projection does not compute a new transitive dependency graph. It also does not guess which generated files a declaration owns: current compiler analysis and Canonical IR do not materialize a per-declaration generated-artifact mapping, so `generatedArtifacts.status` is `unknown`, the artifact list is empty, and the result includes an explicit reason.

Compatibility outcomes require two project states and remain owned by the existing M7 `aidl diff` classifier. When impacted evidence touches API/client, event/topic, or persisted-schema surfaces, `compatibilityChecks` records `aidl diff` with `status = requiresComparison`; it never predicts a safe/breaking result from a single state.

## Determinism and bounds

Results are sorted by stable declaration identity. The machine contract bounds output to:

- 128 directly affected declarations;
- 128 public-contract evidence entries;
- 128 persisted-state evidence entries;
- 32 relevant compatibility-check entries.

`totals` records complete counts before truncation and `truncated` identifies each bounded list independently. Generated artifacts use an explicit evidence-status object rather than an inferred list.

## CLI behavior

Human output is a compact projection of the same facts as JSON output. JSON uses the shared closed CLI envelope with `command = "impact"`.

Exit codes follow the established convention:

- `0`: the FQN resolves and impact evidence is emitted;
- `1`: compiler errors, invalid/unknown/ambiguous FQN, or an expected impact/IR build failure;
- `70`: unexpected internal failure.

M8-06 advances the current closed CLI schema to `spec/cli-output-v6.schema.json`. Frozen v1-v5 schema artifacts remain unchanged.

## Non-goals

This capability does not add language rules, generator ownership metadata, repository heuristics, hypothetical change classification, transitive dependency semantics, or coding-agent workflow documentation.

# M16.5 candidate-readiness recovery

Status: **experimental/evidence-only recovery**. Project base: `49866a14d263c9dbf4269f46642d7e86936114cf` (`main`). This package prepares the internal E3-E7 prototype evidence needed for a truthful later E8 candidate run. It does **not** execute the frozen current-surface run, execute a candidate run, compare before/after results, select a preferred language surface, start E9, or alter production AIDL behavior.

## Hard boundary

No production grammar, lexer/parser acceptance, production AST/Canonical IR authority, formatter/migrator, IntelliJ/LSP completion, production diagnostics, runtime/generator, M7 compatibility/support/conformance, release behavior, or project `.ai/**` is changed. The integrated current-surface external runner is untouched. The frozen M16 corpus and before-baseline remain the authority for a later evaluation and are not edited by this recovery.

## Immutable prototype identities

Content-changing prototype schemas use new exact identities rather than mutating prior tuples:

- E3 candidate schema: `urn:aidl:schema:language:m16.5-e3-candidate` / `m16.5-e3-candidate-v2` / `sha256:367b920826a5c85ced83e58ddaec959e8539064e4f04e49486655c54bf695d85`.
- E4 introspection schema: `urn:aidl:schema:meta:m16.5-e4-introspection` / `0.2.0-e4` / `sha256:68465a548d3322af3ae2d14df018fde1f08cdd161ce864f648f96a32a20dfdf2`.
- E5 current schema remains unchanged: `urn:aidl:schema:language:m16.5-e5-current` / `m16.5-e5-current-v1` / `sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822`.
- E5 candidate schema: `urn:aidl:schema:language:m16.5-e5-candidate` / `m16.5-e5-candidate-v2` / `sha256:b30abd7f3534e7792c041ecf1e67f22c264be05712324a36096056dde5cebaf5`.

E6, E7 and the readiness harness require these exact tuples. The previous E3/E4/E5-candidate versions are stale for changed content and fail closed. There is no `latest`, source sniffing, fallback parsing, implicit source-version selection, or implicit migration state.

## Fact-complete normalization evidence

E3 v2 keeps the isolated common-structure experiment but makes the five previously lossy shapes explicit:

- projection `source` is repeatable, preserving multi-source membership and order;
- index fields carry identifiers plus optional `asc`/`desc` direction;
- dead-letter shape carries the attempt threshold;
- schedule-lease shape carries singleton mode plus lease duration;
- Sync-outbox shape carries change target plus explicit `outbox` delivery.

E5 candidate v2 replays every normalization row through E3 v2 without client translation and now rewrites multi-source projection without dropping sources. Old-source parsing still uses the production parser where it already worked. The existing tooling parser's schedule declaration gap remains narrowly bounded to the recorded `expected declaration` condition; production parser behavior is not repaired or broadened here.

## Compiler/profile-owned introspection evidence

E4 remains a read-only experimental metadata service. Representative detailed declaration shapes remain App, Entity, Service and Sync, while `ConstructionSurface` records bounded construction/fact projections for the additional current-language surfaces needed by the frozen evaluation. The mapping is surface/schema based and contains no task-ID allowlist.

Generic sublanguage vocabularies come from normative project sources, not from evaluation-task wording:

- `profileProperty`: service reliability stores from `docs/07-distributed-systems.md` (`idempotencyStore`, `inboxStore`, `workflowStore`, `projectionStore`, `syncStore`);
- `uiStatement`: typed UI words demonstrated by `docs/03-frontend.md`;
- `testStatement`: typed test verbs demonstrated by `docs/05-diagnostics-testing.md`.

E6 exposes only E4-owned current construction/vocabulary metadata or an exact E5 dry-run migration replacement. E7 diagnoses only against E4-owned structural/vocabulary facts and projects migration/deprecation diagnostics only from the exact explicit E5 context. Neither consumer owns a second language schema.

## Derived readiness gate

`tools/m16_evaluation_harness.py` no longer has an unconditional `ready=false` or a task-ID success allowlist. Candidate readiness is derived by joining:

1. exact E3/E4/E5 immutable identities;
2. E4 construction surfaces and their semantic-fact projections;
3. E3 candidate surfaces gated by E5 fact-complete replay rows;
4. closed generic E4 vocabularies independently consumed by both E6 and E7; and
5. each frozen task's declared `requiredSurfaces` and `expectedSemanticFacts`.

Unknown/missing surfaces, missing semantic-fact projections, empty/mismatched vocabularies, stale schema identities, or incomplete E5 rows keep readiness false with machine-readable per-task reasons. Deterministic tests explicitly degrade each former normalization gap, each generic vocabulary, consumer vocabulary agreement, construction-surface presence and semantic-fact projection to prove that `ready=true` cannot survive missing evidence.

The full-repository test additionally evaluates the unchanged 50-task frozen corpus and asserts zero unavailable tasks. This is an internal readiness check only; it does not run an agent or compiler benchmark and is not E8 evidence.

## Frozen evaluation inputs

On a full checkout the harness tests assert Git blob identity for the protected inputs and runner:

- `fixtures/m16-5/m16-agent-task-corpus.json`: `c8dae3b9babf0c89bcd942a7d0c94a70dc537f82`, corpus fingerprint `sha256:e47b399c2460f576a2f68023af039412f02395de67f8204f3785bf9d7d8dfcef`;
- `fixtures/m16-5/m16-before-baseline.json`: `5ee06d6537ce5457c73bbf571fb72ca17188a2c5`, baseline fingerprint `sha256:d5c7e9cd2003cfa970707e11d8cb130c80aac056028630aa3b7679e2790b7110`;
- `tools/m16_evaluation_runner.py`: `692e3cf1c36c98952786472828934f62a46f30d5`.

The accepted current-surface task authority remains `a5c359b501913f7adce92792dec244add0452909`.

## Local focused validation

Executed in the isolated recovery workspace:

```text
python3 -m compileall -q \
  tools/m16_5_e3_prototype.py tools/m16_5_e4_introspection.py \
  tools/m16_5_e5_migration.py tools/m16_5_e6_completion.py \
  tools/m16_5_e7_diagnostics.py tools/m16_evaluation_harness.py \
  tools/test_m16_5_e3_prototype.py tools/test_m16_5_e4_introspection.py \
  tools/test_m16_5_e5_migration.py tools/test_m16_5_e6_completion.py \
  tools/test_m16_5_e7_diagnostics.py tools/test_m16_evaluation_harness.py
# exit 0

python3 -m unittest -q \
  tools.test_m16_5_e3_prototype tools.test_m16_5_e4_introspection \
  tools.test_m16_5_e5_migration tools.test_m16_5_e6_completion \
  tools.test_m16_5_e7_diagnostics tools.test_m16_evaluation_harness
# 85 tests, OK; 3 full-checkout-only assertions skipped in the isolated workspace
```

The PR's normal GitHub Actions checks are the authoritative full-repository regression evidence, including the real frozen-corpus readiness assertion. No empirical M16/E8 run was executed as part of this validation.

# M16 vendor-neutral evaluation prerequisite for M16.5 E8

Status: **bounded prerequisite evidence only**. Project base: `a5c359b501913f7adce92792dec244add0452909` (`main`).

This package establishes the missing M16 evaluation prerequisite that M16.5 E8 depends on. It does **not** execute an E8 current-vs-candidate comparison, claim a preferred language surface, adopt candidate syntax, or change production language/tooling behavior.

## Existing-infrastructure check

Current `main` already contains `tools/performance_baselines.py` plus `spec/performance-baselines.json`. That contract measures deterministic compiler-structure workloads (`sourceFiles`, `sourceBytes`, declarations, symbols, import resolutions); it is not a model-independent construction/change task corpus or agent run evaluator. The M2 semantic-fixture manifest is likewise a compiler-diagnostic regression corpus rather than an agent task/run benchmark.

This prerequisite therefore adds the missing bounded task/run layer and reuses the repository's existing strict-determinism style rather than duplicating either compiler-performance or M2 semantic infrastructure.

## Frozen vendor-neutral corpus

Fixture: `fixtures/m16-5/m16-agent-task-corpus.json`

- corpus ID: `urn:aidl:evaluation:m16-agent-tasks-v1`
- task count: **50**
- exact fingerprint: `sha256:e47b399c2460f576a2f68023af039412f02395de67f8204f3785bf9d7d8dfcef`
- project base: `a5c359b501913f7adce92792dec244add0452909`
- task IDs are frozen as `m16-001` through `m16-050`
- requirements describe semantic intent and do not teach M16.5 candidate spellings
- each task records construction/change mode, family, pinned initial-project reference, semantic expected facts, and required compiler/prototype surfaces

The 50 tasks cover Core fields/types/modifiers/indexes/invariants, App, Backend service/system, messaging/consumer/dead-letter behavior, workflow/schedule, Sync, API/operations, generic profile/UI/test surfaces, and the E1 normalization relationships. Semantic correctness is evaluated against expected facts, not an exact text diff.

## Reproducible current-surface “before” baseline

Fixture: `fixtures/m16-5/m16-before-baseline.json`

- baseline ID: `urn:aidl:evaluation:m16-current-surface-before-v1`
- exact fingerprint: `sha256:d5c7e9cd2003cfa970707e11d8cb130c80aac056028630aa3b7679e2790b7110`
- accepted current-surface authority: exact project commit `a5c359b501913f7adce92792dec244add0452909`
- frozen context budget: `32000` tokens
- retry limit: `2` retries (`3` attempts maximum)
- seed policy: fixed seed `1605008` where an executor supports deterministic seeding; unsupported seeding must be recorded as unavailable
- task order: ascending frozen task ID
- acceptance commands:
  - `aidl check <task-worktree> --format json`
  - `aidl ir <task-worktree> --format json`
- token accounting: provider/executor totals are recorded when available; absence is an explicit unavailable value with a reason
- human rewrite classification: `none`, `minor`, `substantial`, `rejected`, or `not-reviewed`

This “before” artifact freezes the **current-surface run protocol and inputs**, not an invented model result. No empirical model/vendor measurement is fabricated by this package. A completed future before-run record must bind to both the corpus and baseline fingerprints and use this exact execution contract.

## Deterministic harness/evidence contract

`tools/m16_evaluation_harness.py` is transport-neutral and read-only. It never calls a model, vendor API, network, production formatter/migrator, IDE, or mutation API.

`python3 -m tools.m16_evaluation_harness verify` validates the frozen corpus/baseline, checks pinned repository paths, reads the integrated E4/E5 prototype identities, and reports candidate readiness. Completed external run records are accepted by `summarize` only when they:

1. bind to the exact corpus ID/fingerprint and before-baseline ID/fingerprint;
2. carry the frozen context budget, retry limit, seed policy, task order, and compiler acceptance commands without substitution;
3. contain one ordered result for every frozen task;
4. preserve every raw attempt up to the retry limit;
5. record parse/semantic-validation/compile status, observed semantic facts, false assumptions, invalid combinations, errors, invented syntax, wrong placement, diagnostics, regressions, source-line count, token availability/cost, patch churn, unnecessary edits, and human rewrite class; and
6. carry a canonical SHA-256 fingerprint over the complete run record.

A tampered fixture, mismatched execution contract, stale fingerprint, missing task, excess retry, inconsistent token total, or malformed metric fails closed.

## Aggregation formulas

For each task, final output correctness requires final parse success, semantic-validation success, compile success, all expected semantic facts recalled, zero false assumptions, zero invalid combinations, zero raw errors, and zero regressions. First-pass success applies the same predicate to attempt 1.

The harness reports raw counts before rates:

- `outputCorrectness = outputCorrectTasks / taskCount`
- `firstPassSuccess = firstPassCorrectTasks / taskCount`
- `firstPassParse = firstPassParseTasks / taskCount`
- `firstPassSemanticValidation = firstPassSemanticValidationTasks / taskCount`
- `firstPassCompile = firstPassCompileTasks / taskCount`
- `semanticFactRecall = recalledExpectedFacts / expectedSemanticFacts`
- `diagnosticsPer100SourceLines = diagnostics * 100 / finalSourceLines`
- retries are `sum(attemptCount - 1)`
- missing facts, false assumptions, invalid combinations, errors, invented-syntax events, wrong-placement events, regressions, files touched, lines added/deleted, and unnecessary edits are summed as raw counts
- token totals include only tasks with available accounting; unavailable task count is retained separately
- human-rewrite classifications are counted by the five frozen enum values

`compare_runs()` is implemented for a later like-for-like E8 use, but it refuses a candidate comparison while the integrated prototype readiness check is false. If it eventually becomes valid, deltas are `candidate - before` raw/rate values only; the harness does not convert deltas into a language-preference claim.

## Candidate boundary and explicit unavailable coverage

Candidate readiness is deliberately **false** on current `main`. The harness imports the integrated E4/E5 prototype modules and verifies these exact authorities rather than defining another grammar:

- E4: `urn:aidl:schema:meta:m16.5-e4-introspection` / `0.1.0-e4` / `sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542`
- E5 current: `urn:aidl:schema:language:m16.5-e5-current` / `m16.5-e5-current-v1` / `sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822`
- E5 candidate: `urn:aidl:schema:language:m16.5-e5-candidate` / `m16.5-e5-candidate-v1` / `sha256:c702262d2f5374d8eda54a028923d00d7d21e45d3980c62f32d472392ccc8c30`

Known gaps remain explicit unavailable cases:

- multi-source projection fact loss;
- incomplete index-direction shape;
- incomplete dead-letter threshold shape;
- schedule lease plus the recorded tooling-parser gap;
- incomplete Sync outbox shape;
- missing concrete `profileProperty`, `uiStatement`, and `testStatement` vocabularies from E4;
- every task surface outside E4's representative App/Core/Backend/Sync construction metadata.

There is no `latest` lookup, syntax sniffing, fallback, implicit migration state, second candidate grammar, or client-side semantic reconstruction. E8 must not execute a full candidate benchmark until those gaps are resolved or a later authorized compiler-owned surface covers them.

## Focused validation

Local isolated package validation:

```text
python3 -m compileall -q tools/m16_evaluation_harness.py tools/test_m16_evaluation_harness.py
# exit 0

python3 -m unittest -v tools.test_m16_evaluation_harness
# 17 tests, OK; 2 integration-only tests skipped because the isolated workspace does not contain the full project
```

The 17 tests cover frozen IDs/fingerprints, task wording neutrality, fixture tamper detection, current baseline authority, deterministic aggregation, raw failure retention, retries/churn, unavailable token accounting, retry/context/fingerprint failures, candidate gap reporting, stale E4 rejection, blocked candidate comparison, human-rewrite counts, and two exact-project integration checks. On the real PR checkout those integration checks exercise the integrated E4/E5 identities and the pinned `examples/petstore` initial-project references.

Repository CI remains the authoritative full E3–E7 and project regression gate.

## Remaining work before E8

This prerequisite intentionally leaves E8 unstarted. A later E8 dispatch still needs a genuinely completed current-surface agent run record and, only after candidate coverage becomes truthful for the entire frozen corpus, a candidate run under the identical fingerprints/execution contract. Raw failures and non-improvements must remain visible. No before/after benefit statement is valid until those executions exist.

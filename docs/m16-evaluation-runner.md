# M16 current-surface external evaluation runner

Status: **recovery bridge only**. This tool makes a later truthful current-surface model/executor run reproducible and auditable. It does **not** execute the 50-task empirical baseline by itself, does not run a candidate comparison, does not start M16.5 E8, and does not authorize E9 or candidate-language adoption.

The frozen authorities remain unchanged:

- corpus: `urn:aidl:evaluation:m16-agent-tasks-v1` / `sha256:e47b399c2460f576a2f68023af039412f02395de67f8204f3785bf9d7d8dfcef`
- before baseline: `urn:aidl:evaluation:m16-current-surface-before-v1` / `sha256:d5c7e9cd2003cfa970707e11d8cb130c80aac056028630aa3b7679e2790b7110`
- accepted current-surface task authority: `a5c359b501913f7adce92792dec244add0452909`
- recovery implementation base: `9bf261c6867708a6fc2304eedec11891e85d904d`

`temperature` is intentionally **not** a runner control because it is not present in the frozen `executionContract`. The bridge copies the exact frozen contract and must not add provider-specific controls.

## Existing tooling boundary

`tools/m16_evaluation_harness.py` remains the read-only corpus/baseline validator, run-record validator, aggregator, and later comparison gate. `tools/performance_baselines.py` remains a deterministic compiler-structure workload tool. Neither is an external model/executor transport, so this recovery adds only the missing process bridge in `tools/m16_evaluation_runner.py`; it does not create a second grammar, semantic evaluator, compatibility engine, candidate adapter, migration selector, or syntax fallback.

## Invocation

The bridge accepts a user-supplied external command and keeps credentials outside repository data and command-line arguments. The command receives one JSON request on stdin and must emit exactly one JSON response on stdout. Example shape:

```text
python3 -m tools.m16_evaluation_runner \
  --executor-command "/path/to/external-evaluator-wrapper" \
  --run-id "current-surface-2026-09-10-a" \
  --output /secure/evidence/current-run.json \
  --evidence-dir /secure/evidence/current-run
```

The runner refuses to start if the command is absent. External credentials belong in the caller's environment or secret mechanism; they must not be embedded in the repository or passed in `--executor-command`.

## Request protocol

Protocol ID: `urn:aidl:evaluation:m16-external-executor-v1`, schema version `1`.

Each request contains only:

- surface `current`;
- frozen task identity, mode, family, natural-language requirement, and frozen `initialProject` descriptor;
- attempt number, maximum attempts, and the isolated writable task-worktree path;
- the exact frozen `executionContract` copied from `fixtures/m16-5/m16-before-baseline.json`;
- frozen corpus and baseline fingerprints.

The request deliberately omits `expectedSemanticFacts` and candidate spellings. For `repoPath` tasks, the runner materializes the project with `git archive` from the exact accepted surface-authority commit, even if the runner implementation itself is executed from a later commit. For `emptyModule`, it creates exactly one `module <fixture-name>` declaration. Retry attempts use separate directories cloned from the preceding attempt snapshot so raw attempt states are retained without cross-task contamination.

## Response protocol

The response must echo the exact protocol/surface/task/attempt/fingerprints and byte-semantically attest the frozen `executionContract`. It must contain all of these factual fields:

```json
{
  "schemaVersion": 1,
  "protocolId": "urn:aidl:evaluation:m16-external-executor-v1",
  "surface": "current",
  "taskId": "m16-001",
  "attemptNumber": 1,
  "corpusFingerprint": "sha256:...",
  "baselineFingerprint": "sha256:...",
  "acceptedExecutionContract": {},
  "identity": {
    "provider": "...",
    "model": "...",
    "modelVersion": "...",
    "executor": "...",
    "executorVersion": "...",
    "executorBuild": "...",
    "invocationId": "..."
  },
  "networkPolicy": "executor-defined factual policy used for this invocation",
  "seed": {
    "supported": true,
    "used": 1605008,
    "unavailableReason": null
  },
  "tokenCost": {
    "available": true,
    "inputTokens": 0,
    "outputTokens": 0,
    "totalTokens": 0,
    "unavailableReason": null
  },
  "rawModelOutput": "verbatim model output",
  "assessment": {
    "observedSemanticFacts": [],
    "falseAssumptions": [],
    "invalidCombinations": [],
    "errors": [],
    "inventedSyntax": [],
    "wrongPlacement": [],
    "regressions": 0,
    "unnecessaryEdits": 0,
    "humanRewrite": "not-reviewed"
  },
  "retryRequested": false
}
```

If deterministic seeding is unsupported, `supported` is `false`, `used` is `null`, and `unavailableReason` is mandatory. Token accounting follows the same explicit unavailable rule from the frozen baseline. Empty/unknown factual identity fields are rejected; the bridge does not replace them with inferred provider metadata.

The `assessment` object is external evaluation evidence, not language authority. The bridge does not reconstruct expected semantics from syntax. Compiler acceptance remains separately authoritative through the exact frozen commands below.

## Compiler-owned acceptance evidence

After every external attempt, the runner executes exactly:

```text
aidl check <task-worktree> --format json
aidl ir <task-worktree> --format json
```

`parseSuccess` is derived from compiler error diagnostics in the parse phase; `semanticValidationSuccess` requires parse success plus `aidl check` success; `compileSuccess` is derived from `aidl ir` success. The runner records the complete JSON/stdout/stderr evidence and command-output SHA-256 values. It never accepts model assertions for these three statuses.

A compiler failure or explicit `retryRequested=true` causes a retry until the frozen `retryLimit=2` is exhausted. Every attempt is retained. The final record uses the existing `tools.m16_evaluation_harness` structure and is fingerprinted, validated, and summarized by that existing harness before the output file is atomically published.

## Raw evidence and provenance

For each task attempt, the evidence directory retains the sanitized request, raw external stdout/stderr, raw model output, worktree before/after fingerprints, exact model/executor/build/invocation identity, recorded network policy, seed support/use, token accounting, and raw `aidl check`/`aidl ir` stdout/stderr. The completed run record embeds the same audit evidence plus the external command argv fingerprint and runner protocol identity.

The bridge contains no timestamps or random values in the completed record. With the same run ID, command identity, executor outputs, compiler outputs, and produced files, the run-record fingerprint is stable. Temporary physical paths are normalized to `<task-worktree>` before they enter the record fingerprint.

## Fail-closed conditions

No completed benchmark record is published when any of these occurs:

- external command missing or process exit nonzero;
- malformed response JSON;
- protocol, surface, task, attempt, corpus fingerprint, baseline fingerprint, or frozen-contract mismatch;
- missing factual provider/model/executor/build/invocation identity;
- seed attestation inconsistent with fixed seed `1605008` or missing unsupported reason;
- unavailable token accounting without an explicit reason;
- malformed compiler JSON or exit-status/JSON disagreement;
- inability to materialize a frozen `repoPath` from exact surface authority.

Raw per-attempt files already written to the evidence directory remain available when the run fails closed. A failed/partial run is not passed to `summarize` and is not an empirical M16 baseline result.

## Focused recovery validation

The deterministic test suite uses only local mock processes; no model provider is contacted and no mock output is benchmark evidence. It covers protocol validation, isolated pinned-project materialization, retry snapshots, seed/token unavailable semantics, exact compiler-check plumbing, provenance capture, missing/mismatched identity rejection, process/compiler failure, the absence of invented `temperature`, and stable run-record generation.

```text
python3 -m compileall -q tools/m16_evaluation_runner.py tools/test_m16_evaluation_runner.py
python3 -m unittest -v tools.test_m16_evaluation_runner
python3 -m unittest -v tools.test_m16_evaluation_harness
```

The actual 50-task current-surface before run remains a separate future operation. It becomes possible only when a real external command implementing this protocol is supplied with truthful model/executor/build/invocation identity and credentials outside the repository. Candidate evaluation remains blocked independently until the existing M16.5 E3-E7 coverage gate becomes truthful for the frozen corpus.

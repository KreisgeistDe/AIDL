# M16.5 candidate-surface external evaluation runner prerequisite

Status: **evaluation-only implementation prerequisite for a later E8 dispatch**. Project base: `411f3b375a014cedfe4d6899e996f225ee07eefb` (`main`). This package does not execute the frozen empirical evaluation, contact a model/provider, compare current and candidate runs, select a preferred surface, start E9, or change production AIDL behavior.

## Fixed authorities

The candidate runner preserves the frozen M16 corpus, before-baseline and current external-executor contract byte-for-byte. It reuses protocol `urn:aidl:evaluation:m16-external-executor-v1` version `1`; candidate requests have the same fields and frozen `executionContract` as the current runner, with only `surface` set to `candidate`.

Candidate output is never compiler authority. Admission is pinned to the integrated projection contract:

- projection ID `urn:aidl:evaluation:m16.5-candidate-current-projection`;
- version `1`;
- fingerprint `sha256:a99667aecc90877da362f51fdf4fb7f5775b2f3ceb5a2911871f73443f52136c`.

The projection itself pins the exact E3/E4/E5 schema identities and derives its inverse from E5 fact/rule authority. The runner performs no syntax sniffing, latest-version lookup, fallback parse, task allowlist, expected-answer lookup, semantic reconstruction, or second language table.

## Candidate initial worktree

The frozen task descriptor is unchanged. `repoPath` and `emptyModule` inputs are first materialized by the unchanged current runner from the exact frozen current-surface authority. Every `.aidl` source is then moved to the bounded candidate spelling only through explicit E5 current/candidate versions, schema fingerprints and source fingerprint. The integrated candidate projection must immediately round-trip that source back to the same E5 semantic facts; otherwise initialization fails closed before an external executor is invoked.

Retries clone the preceding candidate worktree exactly as the current runner clones its current worktree. Repeated facts keep their original order and multiplicity because neither the runner nor the integrated projection sorts or reconstructs them.

## External executor contract

`tools/m16_5_candidate_evaluation_runner.py` delegates request construction and response validation to `tools/m16_evaluation_runner.py`. This is intentional: the frozen current runner remains byte-identical and continues to own the transport-neutral protocol contract. Candidate mode changes only the explicit `surface` value to `candidate` and records the exact projection reference in audit evidence.

A real later invocation has the same command shape as the current runner:

```text
python3 -m tools.m16_5_candidate_evaluation_runner \
  --executor-command "/path/to/external-evaluator-wrapper" \
  --run-id "candidate-surface-run-id" \
  --output /secure/evidence/candidate-run.json \
  --evidence-dir /secure/evidence/candidate-run
```

Credentials remain external to the repository and command arguments. This implementation does not supply or invoke a model by itself.

## Compiler-authoritative acceptance

After each external attempt, the candidate worktree is passed to `tools.m16_5_candidate_projection.project_worktree(...)` with the exact pinned projection context. Successful projection creates a separate accepted/current worktree and invokes the unchanged production compiler for the frozen acceptance checks:

```text
aidl check <task-worktree> --format json
aidl ir <task-worktree> --format json
```

The candidate runner derives parse, semantic-validation and compile status only from projection/production-compiler evidence. It does not accept executor assertions for those statuses. A missing or ambiguous inverse fact, unsupported/unmodeled candidate construct, stale projection identity, projection failure or compiler rejection cannot become a successful attempt. Projection failures are retained as explicit failed attempt evidence so the frozen retry contract can operate without silently admitting candidate text.

Every attempt records the original candidate worktree fingerprints and patch metrics plus the exact projection identity and compiler evidence. The final run record remains a normal harness record with `surface: candidate`, the unchanged corpus/baseline fingerprints and unchanged frozen execution contract.

## Focused deterministic evidence

`tools/test_m16_5_candidate_evaluation_runner.py` uses a deterministic fake external executor only; it is not benchmark evidence. The tests verify:

- candidate request/response shape is the frozen current protocol with only the surface value changed;
- exact projection identity is mandatory;
- E5 candidate initialization round-trips semantic facts and preserves repeated-source order/multiplicity;
- an independently authored supported candidate project reaches unchanged production `aidl check`/`aidl ir` acceptance through the integrated projection;
- missing, ambiguous and unmodeled candidate facts remain unavailable;
- the known schedule/compiler rejection remains rejection;
- a fake-executor end-to-end adapter run produces a candidate run record without altering the frozen execution contract;
- frozen corpus, before-baseline and current runner Git blobs remain byte-identical; and
- the candidate runner contains no second normalization/syntax table or expected-answer logic.

Repository-required GitHub Actions remain the authoritative full-checkout regression gate. No E8 empirical run or before/after claim is created by these tests.

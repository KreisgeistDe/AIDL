# M7 Compatibility CI Policy

M7-06 adds a CI-only policy boundary over the already-authoritative M7 diff, compatibility-classification, and migration-guidance outputs. It does not add or reinterpret AIDL, Canonical IR, semantic-diff, compatibility, or migration semantics.

## Ownership boundary

`tools/ir_compatibility_ci.py` invokes the production `aidl diff --format json` command for each configured comparison target and then evaluates only the returned `result.changes`, `result.classifications`, and `result.guidance`.

The policy never reparses AIDL semantics, synthesizes diff paths, matches compatibility rule IDs, or invents migration steps. It verifies only cross-output structural invariants needed to trust the three same-order M7 projections.

The workflow owns only checkout, baseline selection inputs, invocation, artifact upload, and propagation of the policy exit status. Compatibility targets live in `.github/aidl-compatibility-targets.json`, not in workflow YAML.

## Deterministic decision mapping

The CI decision is intentionally conservative:

| Existing compatibility class | CI decision | Exit |
| --- | --- | ---: |
| `safe` | `pass` | `0` |
| `conditional` | `review` | `2` |
| `migration-required` | `review` | `2` |
| `breaking` | `fail` | `3` |

A report containing multiple changes uses the strictest decision. No diff is `pass`.

`review` is non-zero in CI. Conditional or migration-required changes therefore cannot be silently treated as safe; a human or higher-level integration process must inspect the machine-readable report and the unchanged authoritative guidance.

## Guidance invariants

The CI policy does not use guidance text to derive compatibility. It checks only generic state consistency:

- every classification and guidance entry must reference the same `kind` and `path` as its M7 diff fact,
- guidance class and `classificationRule` must match the M7 classification output,
- `safe` guidance must have no phases or preconditions,
- `conditional` and `breaking` guidance must not contain rollout phases.

Violations are policy/invariant errors, not compatibility findings.

## Baseline selection

For a pull request, the comparison baseline is `github.event.pull_request.base.sha`, while the current side is the actual pull-request head SHA. The transport branch is never involved.

For a push to `main`, the baseline is `github.event.before` and the current side is the pushed head SHA. The resolver rejects a self-comparison and a zero/absent previous SHA instead of incorrectly reporting no diff.

## Report contract

The per-target report projects the authoritative `changes`, `classifications`, and `guidance` arrays unchanged and adds only CI decision metadata: `status`, `decision`, `exitCode`, class counts, and per-item decision/guidance counts.

Configured target reports are aggregated in declared order. The current M7-06 registry tracks the supported runnable Petstore AIDL contract. Additional contracts must be registered explicitly in `.github/aidl-compatibility-targets.json`.

Producer/compiler/IR/diff failures remain distinct from compatibility findings. A failed `aidl diff` envelope produces `status: "error"` and exit `1`; policy shape/invariant failures and unexpected internal failures exit `70`.

## Validation

`tools/test_ir_compatibility_ci.py` covers no-diff, all four classes, strictest-decision aggregation, raw M7 projection preservation, guidance invariants, deterministic output, producer failure separation, actual PR-base selection, previous-SHA push selection, self-diff rejection, and configured target path invocation.

The normal Compiler/Python gate includes those focused tests. The dedicated `Compatibility / Pull Request` job produces `aidl-compatibility-report.json` as an Actions artifact and applies the report exit status only after artifact upload.

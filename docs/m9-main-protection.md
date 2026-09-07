# M9-06 main protection contract

M9-06 requires `main` to accept project changes only through pull requests whose required checks have succeeded. Repository workflows define the checks; repository rules enforce that they cannot be bypassed by a direct branch update or an unchecked merge.

The machine-readable project contract is `spec/m9-main-protection.json`. `python3 -m tools.validate_main_protection_contract` verifies offline that every required check context is still defined by a workflow that runs for pull requests targeting `main`, and that the intended repository-rule contract retains pull-request enforcement, required status checks, deletion/non-fast-forward protection, linear history, squash-only merge, review-thread resolution, and no bypass.

## Required pull-request checks

The repository ruleset for `refs/heads/main` must require all of these exact check contexts:

- `Compiler / Python`
- `Compatibility / Pull Request`
- `Golden Fixtures`
- `Petstore Runtime / PostgreSQL`
- `IntelliJ Plugin`
- `Reject .ai changes on project PRs`

The first five are jobs in `.github/workflows/python-validation.yml`. The `.ai/**` boundary check is the job in `.github/workflows/protect-ai-workflow-boundary.yml`. The boundary workflow remains project-side enforcement only; operational agent state belongs exclusively on `agents/channel` and project branches must not contain `.ai/**`.

## Required repository rules

The active repository rules for `refs/heads/main` must include:

- pull-request-only changes;
- all six required status checks above;
- deletion protection;
- non-fast-forward protection;
- required linear history;
- resolved review threads before merge;
- squash as the only allowed merge method;
- no bypass actor for ordinary project changes.

Workflow success alone is not sufficient evidence for M9-06. The milestone is complete only when the active GitHub repository rules require these checks and a direct update to `main` cannot bypass them. Repository-rule configuration is intentionally external to the project tree; the checked-in contract makes the expected state deterministic and reviewable without pretending that a workflow can protect its own branch.

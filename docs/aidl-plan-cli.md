# `aidl plan` — Deterministic IR Plan CLI

## Scope

M3-09 adds `aidl plan <path> [<path> ...] [--deployment <selector>]` as the second
production compiler CLI surface after M3-08 `aidl ir`.

The command is read-only. It does not modify source files, deployment state, databases,
resources, generated code, or lockfiles. It also does not implement production
`aidl check`, compatibility diffing against a historical baseline, shared JSON command
envelopes, or the final cross-command exit-code taxonomy.

## IR-first boundary

`aidl plan` reuses the complete M3-08 source-to-canonical-IR pipeline and then calls
`tools/ir_plan.py`. The planner consumes canonical IR only; it never reparses AIDL
source and does not introduce new language semantics.

The plan therefore inherits the M3-01..08 contracts for resolved identity, semantic
defaults, canonical semantics, versioning, semantic hashes, compiler error gating, and
deterministic source-to-IR production.

## Deployment selection

Without `--deployment`, the planner selects `app.defaultDeploymentId` from canonical IR.
With `--deployment`, the selector must match exactly one deployment by stable
`declarationId`, FQN, or declaration name. Zero or ambiguous matches fail without
producing plan stdout.

## Plan document

The M3-09 plan document is a deterministic JSON projection with:

- `planVersion: "0.1.0"`;
- the source `irVersion` and `sourceSemanticHash`;
- stable app and system declaration IDs;
- the selected deployment identity, environment, and regions;
- a sorted `actions` array derived only from canonical deployment/system IR.

Action kinds are intentionally descriptive and read-only:

- `bindResource` for deployment resource bindings;
- `deployService` for deployment service bindings;
- `exposeApi` for system API IDs;
- `activateTopic` for system topic IDs.

Each action references stable IR IDs. Adapter values come directly from canonical
IR deployment bindings. M3-09 does not infer missing bindings or adapter semantics.

## Determinism and output

Actions are sorted by action kind, target declaration ID, and adapter. JSON object keys
are lexicographically sorted, compact UTF-8 JSON is emitted, non-finite numbers are
rejected, and output has exactly one trailing LF.

The source IR semantic hash is copied into `sourceSemanticHash`, allowing scripts and
agents to associate a plan with the exact semantic IR input that produced it.

## Errors

Compiler diagnostics with `error` severity block planning exactly as they block
`aidl ir`. IR-build failures and plan-selection/shape failures are written to stderr;
no partial plan JSON is emitted to stdout.

## Examples

```bash
./aidl plan path/to/project
./aidl plan path/to/project --deployment production
python3 -m tools.aidl_cli plan path/to/project --deployment demo.production@1
```

## Validation

`tools/test_aidl_plan.py` verifies deterministic IR-only planning, canonical stdout,
default and explicit deployment selection, stable action ordering, compiler-error
gating, unknown-deployment failure, and invalid-IR rejection. Python validation runs
these tests alongside M3-01..08 regressions, the full Python suite, repository spec lint,
and the existing Petstore parser smoke.

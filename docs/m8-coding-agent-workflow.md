# M8-07 — Recommended coding-agent workflow

This workflow is the supported repository-level loop for a coding agent that needs to understand and change an AIDL project without inventing language semantics or scanning unrelated source. It uses only existing project files, the production `aidl` CLI, and committed tests.

## Preconditions and boundaries

Start from the repository root and read `AGENTS.md` plus any task-specific project documentation before editing. Select the AIDL project path from the task/repository structure; there is no `aidl discover` command. Do not infer a fully qualified name from filenames: use compiler-named FQNs already visible in source/project context, and let `aidl inspect` validate the exact declaration identity.

For machine consumption, prefer `--format json`. The established CLI process contract is:

- exit `0`: successful command;
- exit `1`: expected validation/build/selection failure;
- exit `70`: unexpected internal error.

A JSON-mode command writes the stable shared envelope to stdout. Treat `ok: false`, compiler diagnostics, and command-specific `error.kind` as authoritative failure evidence rather than repairing around them.

`aidl dependencies <FQN> --format json` now returns both the direct M8-03 relation and the bounded cycle-safe M8-08 transitive closure. Direct results remain in `dependencies`; indirect reachability is in `transitiveDependencies`, with independent totals/truncation metadata. Human output intentionally remains the compact direct-only view for compatibility.

## Executable workflow

The committed `fixtures/valid/m4-minimal` project is the regression example. Its entity FQN is `fixtures.valid.m4minimal.SnapshotItem`.

### 1. Establish a clean compiler baseline

Validate the selected project before reasoning from it:

```bash
./aidl check --format json fixtures/valid/m4-minimal
```

Proceed only when the process exits `0` and the JSON envelope has `ok: true`. On exit `1`, use the returned compiler diagnostics as the source of truth and fix the project before planning or inspection.

### 2. Read the current plan

Ask the existing planner for the deterministic deployment/runtime projection:

```bash
./aidl plan fixtures/valid/m4-minimal --format json
```

Record the resulting plan only as current-state evidence. `aidl plan` is read-only and does not predict a historical compatibility result.

### 3. Inspect only the semantic context needed for the change

Resolve the exact compiler-owned FQN and inspect its Canonical-IR projection:

```bash
./aidl inspect fixtures.valid.m4minimal.SnapshotItem fixtures/valid/m4-minimal --format json
```

A successful result has exit `0`, `ok: true`, and `result.status: "resolved"`. Invalid, unknown, ambiguous, compiler-error, or inspect-build results exit `1`; do not substitute repository text heuristics for a failed compiler lookup.

Use other implemented agent commands only when the task needs their evidence:

- `summary` for bounded project context;
- `dependencies` for direct and transitive compiler/Canonical-IR dependencies;
- `explain` for compiler-emitted rule/evidence/remediation metadata;
- `impact` for the current compiler/Canonical-IR change-impact boundary.

The IDE-facing `resolve`, `complete`, `document`, `usages`, and `rename` commands are also production CLI surfaces, but they are source-position/refactoring APIs rather than the default FQN workflow.

### 4. Make the smallest project change

Edit the relevant project source/test/documentation according to the task. Do not edit generated outputs by hand and do not mutate project `.ai/**`. The editor or patch mechanism is outside the AIDL CLI contract; no synthetic `aidl edit` command exists.

### 5. Re-run compiler validation

Immediately re-run the same project check:

```bash
./aidl check --format json fixtures/valid/m4-minimal
```

Do not continue while compiler errors remain. When a diagnostic needs explanation, `aidl explain <FQN> ... --format json` may be used, but remediation remains limited to compiler-authorized `allowedFixes`.

### 6. Re-read plan and targeted declaration

Re-run the same deterministic projections after the edit:

```bash
./aidl plan fixtures/valid/m4-minimal --format json
./aidl inspect fixtures.valid.m4minimal.SnapshotItem fixtures/valid/m4-minimal --format json
```

Compare only evidence the commands actually expose. For old/new semantic diff, compatibility classification, and migration guidance, use the existing two-state `aidl diff` workflow rather than inferring compatibility from `inspect`, `plan`, or `impact` alone.

### 7. Run relevant regressions

Run the focused regression that executes this workflow and the command-contract suites that protect its surfaces:

```bash
python3 -m unittest tools/test_m8_agent_workflow.py tools/test_aidl_check.py tools/test_aidl_plan.py tools/test_cli_output_schema.py
```

Then use the repository's normal validation/CI gate for the complete change. A project PR is not complete while required GitHub Actions fail or while its diff contains project `.ai/**` mutations.

## End-to-end regression contract

`tools/test_m8_agent_workflow.py` copies `fixtures/valid/m4-minimal` to an isolated temporary project and executes the documented baseline `check`, `plan`, and targeted `inspect` steps in JSON mode. It applies a small supported entity-field constraint change, repeats all three commands, verifies successful machine-readable envelopes, and asserts that the command/test spellings documented above remain available. M9-01 discovery runs this test in Compiler / Python, while M9-02 also certifies it as part of the CLI-regression inventory.

The workflow does not add a repository scanner, a synthetic edit/build/test command, PSI-local semantic fallback, or language semantics beyond the compiler-owned surfaces documented by their own regressions.

# M8-02 — `aidl inspect <FQN>`

M8-02 adds deterministic declaration-level semantic inspection for coding agents without adding language semantics, dependency analysis, diagnostic explanation, project summaries, change-impact analysis, or IntelliJ PSI ownership.

## Command

```text
aidl inspect <FQN> [PATH ...] [--format human|json]
```

`<FQN>` is the compiler-owned fully qualified declaration name, for example `demo.Pet`. `PATH` accepts AIDL files or directories and defaults to the current directory so the shortest project-root form is `aidl inspect demo.Pet`. Human output is the default; `--format json` uses the current versioned CLI JSON contract.

## Semantic boundary

Inspection resolves the requested name only through `CompilerProject.symbol_table`. A successful lookup must identify exactly one declaration. The returned semantic view contains the compiler-indexed declaration identity/source facts plus the exact matching Canonical-IR node produced by the existing IR builder. The command does not reinterpret parser nodes, invent defaults, resolve dependencies, or consult IntelliJ PSI.

The `canonical` member is intentionally the existing Canonical-IR declaration/app/system/service/resource/deployment object rather than a second semantic model. Its detailed fields therefore remain governed by the Canonical IR contract; the inspect schema additionally requires its stable identity fields.

## Result and exit behavior

A successful inspection exits `0`. JSON output uses `command = "inspect"`, `ok = true`, the normal diagnostics array, and `result.status = "resolved"`.

Expected failures exit `1`:

- syntactically invalid FQN: `result.status = "invalid"`, `error.kind = "invalidFqn"`;
- syntactically valid but missing FQN: `result.status = "unknown"`, `error.kind = "unknownFqn"`;
- duplicate compiler symbols for the same FQN: `result.status = "ambiguous"`, `error.kind = "ambiguousFqn"`;
- compiler errors in the project: `error.kind = "compiler"` with the unchanged compiler diagnostics;
- inability to project the resolved declaration through the existing Canonical IR boundary: `error.kind = "inspectBuild"`.

Unexpected implementation failures retain the repository-wide internal-error contract and exit `70`.

Human success output is compact and deterministic: FQN/kind, module, export visibility, source location, source header representation, and one canonical compact-JSON line. Expected human failures are written to stderr and do not produce success stdout.

## JSON schema compatibility

M8-01 froze the closed v1 command set at `spec/cli-output.schema.json` with schema ID `https://aidl.example/spec/cli/1/cli-output.schema.json`. Because that schema deliberately rejects unknown commands, admitting `inspect` cannot mutate the frozen v1 contract without invalidating its closed-command guarantee.

M8-02 therefore advances the current contract to schema major `2.0.0` in `spec/cli-output-v2.schema.json`, ID `https://aidl.example/spec/cli/2/cli-output.schema.json`. V2 accepts every v1 envelope by reference and adds only the `inspect` envelope. Existing emitted bytes for all v1 commands remain unchanged.

## Scope boundary

M8-02 answers only “what is this fully qualified declaration?” It does not compute incoming/outgoing dependencies, explain diagnostics, summarize a project, predict change impact, or prescribe an agent workflow. Those remain subsequent M8 roadmap items.

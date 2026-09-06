# JSON CLI output for agents and CI

## Scope

M3-11 adds deterministic machine-readable output to the three current agent/CI-relevant
commands: `aidl check`, `aidl ir`, and `aidl plan`. It reuses existing compiler
diagnostics, canonical IR, and plan data without adding language semantics.

Existing human/native contracts remain the defaults. `aidl check` remains human-readable
unless `--format json` is requested; `aidl ir` and `aidl plan` continue to emit their
canonical native JSON payloads unless `--format json` is requested.

## Shared JSON envelope

With `--format json`, stdout contains exactly one compact, sorted-key JSON object followed
by one LF. stderr is empty for command-handled validation/build failures. The common fields
are:

- `command`: `check`, `ir`, or `plan`;
- `ok`: whether the command completed successfully under its existing exit behavior;
- `diagnostics`: the existing compiler diagnostics as stable structured objects.

Successful `ir` and `plan` invocations additionally include `result`, containing the
existing canonical IR or plan object respectively. Command-local build/selection failures
that are not compiler diagnostics use `error` with a stable `kind` and a human-readable
`message`. Failed commands omit `result` rather than emitting partial semantic output.

Examples:

```bash
./aidl check --format json path/to/project
./aidl ir --format json path/to/project
./aidl plan --format json path/to/project
```

`aidl check --format json` returns all compiler diagnostics in compiler-provided order,
including warnings and info diagnostics. An error diagnostic makes `ok` false. The command
does not build IR merely to validate.

## Compatibility boundary

M3-11 does not define the final command-wide exit-code taxonomy; current success/failure
return codes remain in place. It also does not add JSON schemas for the CLI envelope,
which remains later agent-first tooling work, and does not alter canonical IR or plan
semantics.

## Validation

`tools/test_aidl_json_cli.py` covers deterministic check JSON, structured compiler
failures, wrapped canonical IR and plan results, and machine-readable plan-selection
failure. Existing `tools/test_aidl_check.py`, `tools/test_aidl_ir.py`, and
`tools/test_aidl_plan.py` continue to protect the default human/native contracts.

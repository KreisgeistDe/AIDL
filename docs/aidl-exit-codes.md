# AIDL CLI exit-code conventions

## Scope

M3-12 defines the final process exit-code contract for the current agent/CI-relevant
commands: `aidl check`, `aidl ir`, and `aidl plan`. It does not change compiler, IR,
planning, human-readable, or JSON semantics.

## Contract

The commands use the following process exit codes consistently:

- `0` — success. The command completed and produced its normal success output.
- `1` — expected validation/build failure. This includes compiler error diagnostics,
  canonical IR build failures, and plan build/deployment-selection failures that are
  already represented by the command's established human or JSON failure output.
- `70` — unexpected internal error. An unexpected exception escaped the established
  compiler/IR/plan failure boundaries.

Argument-parser usage errors remain owned by `argparse` and keep its standard behavior;
M3-12 does not redefine CLI syntax-error handling.

## Output compatibility

Existing output contracts remain unchanged for success and expected failures:

- default `aidl check` diagnostics remain on stderr;
- native `aidl ir` and `aidl plan` success output remains canonical JSON on stdout;
- `--format json` continues to emit one deterministic shared envelope on stdout and keeps
  command-handled failures off stderr.

For an unexpected internal error, native/human mode emits one concise line to stderr:

`aidl <command>: internal error: <ExceptionType>: <message>`

JSON mode emits the existing shared envelope with `ok: false`, empty `diagnostics`, and
an `error` object whose stable `kind` is `internal`. No partial `result` is emitted.

## Compatibility boundary

The numeric taxonomy is final for the current `check`, `ir`, and `plan` command set.
M3-12 does not add new commands, language semantics, generator/runtime behavior, or
stable JSON schemas for command envelopes.

## Validation

`tools/test_aidl_exit_codes.py` verifies success, expected validation/build failures, and
unexpected internal failures across all three commands in native/human and JSON modes.
The Python validation workflow runs these focused tests together with M3 regressions, the
full Python suite, repository spec lint, and the Petstore parser smoke.

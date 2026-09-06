# `aidl check` — Human-readable validation CLI

## Scope

M3-10 adds production `aidl check <path> [<path> ...]` to the repository-root `aidl`
command.

The command validates a project through the existing compiler analysis and diagnostic
pipeline. M3-10 does not add language semantics, a second validator, shared JSON CLI
output, or the final cross-command exit-code taxonomy.

## Compiler boundary

`aidl check` calls `load_compiler_analysis(...)` and renders the resulting
`CompilerDiagnostic` sequence. The compiler remains the single source of truth for
parsing, resolution, semantic policy, diagnostic codes, severity, ordering, and source
locations.

The CLI does not build canonical IR merely to validate a project and does not reimplement
semantic checks in command-specific code.

## Human-readable output

Each diagnostic is written to stderr in the stable form:

```text
<file>:<line>:<column>: <severity> <code>: <message>
```

Diagnostics are emitted in the deterministic order already provided by
`CompilerAnalysis`. `aidl check` writes no normal payload to stdout.

A supported project with no diagnostics succeeds silently. Diagnostics at warning or
info severity are still rendered; an error diagnostic makes the command unsuccessful.
M3-10 intentionally does not generalize these return values into the later shared
cross-command exit-code policy.

## Relationship to later M3 work

The roadmap separately owns JSON output for agent/CI-relevant commands. Therefore
`aidl check --format json` and any shared command envelope remain later work even though
the compiler library already has a deterministic diagnostic JSON representation.

Likewise, final command-wide conventions distinguishing validation failures from internal
errors remain a separate later M3 task.

## Validation

`tools/test_aidl_check.py` verifies that:

- a valid supported project succeeds without output;
- an invalid project produces source-located human-readable diagnostics and no stdout;
- repeated checks over identical input produce identical output.

Python CI runs these focused tests together with M3-01..09 regressions, the full Python
suite, repository spec lint, and the existing Petstore parser smoke.

# M8 — Diagnostic explanation

`aidl explain <FQN>` gives coding agents a compact, compiler-authoritative explanation of diagnostics associated with one exactly resolved declaration.

## Usage

```text
aidl explain <FQN> [PATH ...]
aidl explain <FQN> [PATH ...] --format json
```

`<FQN>` is an exact compiler-owned fully qualified declaration name. `PATH` accepts AIDL files or directories and defaults to the current directory.

## Authority boundary

The command does not invent language rules, remediation, source heuristics, or repository-wide context. It resolves the requested FQN through the compiler symbol table and projects only diagnostics already emitted by the compiler whose source locations fall within that declaration.

Each explanation is built exclusively from existing diagnostic metadata:

- `rule` contains the existing diagnostic code, phase, message, and, when present, `expected` and `docs`;
- `evidence` contains the existing source location and, when present, structured diagnostic subject metadata;
- `remediation` contains only the diagnostic's existing `allowedFixes`; an empty list means the compiler authorized no fix metadata.

The command does not synthesize fixes from prose, infer missing semantic facts, or reinterpret diagnostics.

## Determinism and bounds

Explanations are sorted by diagnostic source offset, diagnostic code, and message. At most 64 explanations are returned for one declaration. The result includes `totalDiagnosticCount` and `truncated`, so callers can distinguish a complete result from the deterministic bounded prefix.

A clean declaration resolves successfully with an empty explanation list.

## Exit behavior

A resolved declaration exits `0` even when the explanation contains compiler error diagnostics: those diagnostics are the subject of the command rather than a precondition failure.

Invalid, unknown, or ambiguous FQNs exit `1` with the established `invalidFqn`, `unknownFqn`, or `ambiguousFqn` error kinds. Unexpected internal failures remain exit `70` with `error.kind = "internal"`.

## JSON schema

M8-04 adds `spec/cli-output-v4.schema.json`. The frozen v1, v2, and v3 schema artifacts are unchanged. V4 references v3 and adds only the closed `explain` envelope.

Project summaries, change-impact analysis, transitive dependencies, and agent workflow documentation remain outside M8-04.

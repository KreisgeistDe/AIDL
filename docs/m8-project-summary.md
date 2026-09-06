# M8-05 — Compact project summaries

`aidl summary [PATH ...]` provides a bounded compiler-authoritative project overview for coding-agent context. `PATH` accepts AIDL files or directories and defaults to the current directory. Human output is the default; `--format json` uses the current versioned CLI JSON contract.

## Semantic boundary

The summary reuses facts already owned by the compiler project model after normal parsing, resolution, and diagnostics. It does not scan repository text, infer architecture from filenames, build a new dependency graph, inspect generated artifacts, or introduce language semantics.

The result projects:

- document, module, declaration, exported-declaration, and unmoduled-document counts;
- stable declaration-kind counts;
- module summaries with document/declaration/export counts and declaration-kind counts;
- compiler-named declaration identities (FQN, kind, exported flag);
- already-resolved module-to-module import dependencies.

Canonical IR remains the source for canonical declaration semantics used by commands such as `aidl inspect` and `aidl dependencies`; `aidl summary` intentionally stays on the smaller compiler project fact boundary and does not create new IR or dependency semantics.

## Determinism and bounds

All set-like projections are stably sorted. Output is explicitly bounded to:

- 64 module summaries;
- 128 declaration identities;
- 128 resolved module dependencies.

The JSON result carries full totals plus per-list `truncated` flags, so consumers can distinguish a complete compact summary from a bounded prefix. Counts and declaration-kind aggregates are not truncated.

## Exit behavior

- `0`: project analysis has no compiler errors and the summary was emitted;
- `1`: the project has compiler errors; JSON uses `error.kind = "compiler"` and preserves compiler diagnostics;
- `70`: unexpected internal failure; JSON uses the established `error.kind = "internal"` envelope.

Warnings and informational diagnostics may accompany a successful summary through the normal top-level `diagnostics` array.

## Non-goals

M8-05 does not implement declaration change-impact analysis, transitive declaration dependency semantics, generated-artifact impact, or the recommended coding-agent workflow. Those remain separate roadmap items.

# M11-01 Compiler Snapshot API

M11-01 introduces `tools.compiler_snapshot` as the compiler-owned boundary for authoritative analysis of unsaved AIDL buffers.

## Contract

`create_compiler_snapshot(paths, overrides)` performs the existing deterministic `.aidl` discovery for the supplied project paths, reads every discovered saved file, and substitutes an explicit UTF-8 override only for a discovered path named in `overrides`. The resulting immutable `CompilerSnapshot` owns:

- the exact source text analyzed for every project document;
- the normal compiler project and full diagnostic stream, including existing Core type/materialization diagnostics;
- per-file diagnostics over the same snapshot;
- existing compiler-owned resolve, completion, and documentation queries at `file + offset`, using the same snapshot text for both source and target locations.

No override is written to disk. A snapshot without overrides follows the ordinary saved-file compiler path and preserves saved source paths, source locations, diagnostic codes, and deterministic ordering.

## Unsaved-buffer behavior

The thin LSP adapter now keeps full-text overrides only as protocol state. `didOpen` and full-document `didChange` text feed `create_compiler_snapshot`; diagnostics and definition are then computed from that snapshot. `didSave` drops the override and returns to the saved file, and `didClose` drops the override and clears published diagnostics. LSP UTF-16 conversion remains transport-only; parser, name-resolution, type, diagnostic, completion, and documentation semantics remain compiler-owned.

The LSP advertises full text synchronization (`TextDocumentSyncKind.Full`) rather than implementing incremental text patches. Incremental compiler state and cache invalidation belong to M11-03.

## Determinism and isolation

Snapshot discovery order is the existing `iter_aidl_files` order. Overrides are normalized by filesystem path and may replace only already-discovered project files. A separate snapshot receives a separate immutable source-text mapping and analysis, so one editor buffer cannot mutate another snapshot or the saved project.

An override for a path outside the discovered project is rejected. This is deliberate: deciding whether an unsaved new file belongs to a workspace, and assigning multi-root ownership, belongs to M11-02 rather than M11-01.

## Explicit non-goals

M11-01 does not add workspace discovery, workspace-folder or multi-root ownership, unsaved new-file admission, incremental parsing, caches, watched-file handling, cancellation/progress, completion/hover/references/rename LSP methods, or new AIDL language semantics. Those remain later M11 work.

Focused regressions live in `tools/test_compiler_snapshot.py` and `tools/test_aidl_lsp.py`. They cover authoritative overrides, saved-file fallback, snapshot isolation, rejected foreign overrides, unsaved diagnostics, unsaved definition, and the existing resolve/completion/documentation APIs over one snapshot.

# M11-04 compiler-owned LSP semantic capabilities

M11-04 exposes the compiler-owned editor semantics that already existed before the production LSP work. The LSP remains a protocol adapter: it does not implement an alternate name resolver, completion engine, documentation model, reference search, rename policy, or quick-fix policy.

## Snapshot authority

Every semantic request selects the owning root through `IncrementalCompilerState` and runs against that root's exact `CompilerSnapshot`, including unsaved full-text overrides. Independent roots never share semantic candidates, usages, rename edits, or diagnostic fixes.

The server advertises and implements:

- `textDocument/completion` from `CompilerSnapshot.complete()`;
- `textDocument/hover` from `CompilerSnapshot.document()`;
- `textDocument/references` from compiler-owned snapshot usage discovery;
- `textDocument/prepareRename` and `textDocument/rename` from compiler-owned unique resolution and conservative snapshot rename planning;
- `textDocument/codeAction` only for explicit compiler diagnostic `allowedFixes` that the compiler-owned edit planner can map safely.

`textDocument/definition` and diagnostics continue to use the same owning incremental snapshot.

## Conservative mapping

Completion returns only compiler candidates and preserves compiler insertion text plus FQN detail. Unresolved, ambiguous, or invalid completion contexts return no candidates.

Hover renders only compiler declaration documentation and diagnostics. It does not inspect raw source text for fallback semantic meaning.

References are locations that resolve to the same unique compiler target inside one snapshot. Import references are ordinary semantic usages when the resolver identifies them; declaration locations are not reported as usages.

Rename requires a compiler-clean snapshot, a uniquely resolved target, a valid non-keyword identifier, no FQN collision, and exact source-text matches for every compiler-planned occurrence. LSP receives only the resulting workspace edit; it never writes project files itself. Unsaved buffers participate because all edits are planned against snapshot text.

Code actions are even narrower. The LSP cannot invent a fix from a diagnostic message. The compiler-owned planner accepts only an existing `allowedFixes` entry and currently maps only the established `insertClause` fix kind. Unknown fix kinds or unsafe insertion anchors produce no action.

## Protocol state

All semantic requests use the M11-03 cancellation token and optional work-done progress path. Cancellation returns the LSP request-cancelled error and does not publish a partial semantic result. Watched-file and open-buffer changes continue to invalidate the owning compiler root before subsequent requests.

## M11.8 boundary

M11-04 preserves the compiler results that are already available, but it does not define the final protocol contract for semantic identities, diagnostic identity payloads, edit versioning, document versions, or explicit edit preconditions. Those protocol-preservation requirements remain M11.8. No client should infer stronger preconditions from the current workspace-edit shape.

Focused regressions live in `tools/test_aidl_lsp_capabilities.py` plus the existing LSP, snapshot, workspace, incremental-state, completion, documentation, and refactoring suites.

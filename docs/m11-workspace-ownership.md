# M11-02 Workspace Discovery and Ownership

M11-02 introduces `tools.compiler_workspace` as the compiler-owned boundary between configured workspace roots and per-root compiler snapshots.

## Root contract

Configured roots are normalized to absolute resolved paths, de-duplicated, and sorted deterministically. Root input order therefore cannot change semantic output.

Every AIDL source belongs to at most one configured root. Ownership uses the most-specific containing root: when roots overlap, a file beneath the nested root belongs to that nested root rather than also appearing in the parent-root project. Equal normalized roots collapse to one root. A path outside all configured roots is unowned.

This rule applies before parsing or semantic analysis. It prevents recursive discovery on a parent root from importing a nested independent project into that parent's symbol table.

## Isolated snapshots

`create_compiler_workspace(roots, overrides)` discovers saved `.aidl` files, assigns each discovered path to exactly one owner, and builds one independent `CompilerSnapshot` per root from only that root's owned files. Declarations, imports, diagnostics, resolution targets, completion candidates, and documentation queries therefore cannot cross root boundaries.

No language rule is reimplemented by workspace code. Each isolated snapshot still invokes the existing parser, compiler project, type/materialization, diagnostic, resolution, completion, and documentation paths.

For one root with no overrides, analysis remains equivalent to the ordinary saved-file compiler path.

## Unsaved new files

An explicit in-memory override may either replace an owned saved file or admit a new unsaved source when all of the following hold:

- the path ends in `.aidl`;
- the normalized path is contained by a configured root;
- the normal most-specific-root rule yields one owner.

The file does not need to exist on disk. Its text is analyzed only inside its owning root's snapshot. Unsaved files outside configured roots and non-AIDL override paths are rejected.

## LSP boundary

The thin LSP adapter accepts one or more configured roots and rebuilds a compiler workspace for each semantic query. `didOpen` and full-text `didChange` state can therefore admit a new unsaved `.aidl` file safely. Diagnostics and definition always use the snapshot selected by compiler workspace ownership, so a declaration in another configured root is not a fallback semantic candidate.

The proof does not dynamically adopt client-provided workspace folders. Roots are fixed by server configuration/launch arguments; `workspaceFolders` change notifications are not advertised. Dynamic workspace-root lifecycle is intentionally not mixed with the ownership contract.

## Determinism and failure behavior

- root ordering is canonical and independent of caller order;
- ownership is based only on normalized path containment and root specificity;
- each path appears in at most one snapshot;
- unknown/out-of-workspace overrides fail instead of creating an implicit project;
- overlapping roots are not ambiguous: the most-specific root wins;
- no cross-root declaration, diagnostic, navigation target, or edit authority is created.

## Non-goals

M11-02 does not add incremental analysis, cache invalidation, watched-file handling, cancellation, progress, lifecycle/load testing, dynamic workspace-folder mutation, or new AIDL semantics. Those state-management and performance concerns begin with M11-03.

Focused regressions live in `tools/test_compiler_workspace.py` and `tools/test_aidl_lsp.py` and cover root-order determinism, independent-root isolation, overlapping roots, unknown files, unsaved-new-file admission, saved-file parity, and LSP cross-root isolation.

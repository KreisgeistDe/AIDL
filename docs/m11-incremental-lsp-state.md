# M11-03 Incremental Compiler and LSP State

M11-03 introduces `tools.compiler_incremental` as the compiler-owned state boundary between deterministic workspace inputs and immutable per-root compiler snapshots.

## Incremental contract

Each configured workspace root has an independent cache entry. Before semantic work, the compiler derives the exact owned source set using the M11-02 ownership rules and computes a SHA-256 fingerprint over the normalized root, normalized source paths, and exact UTF-8 source text after unsaved overrides are applied.

If the fingerprint is unchanged, the existing immutable `CompilerSnapshot` is reused. If any owned saved or unsaved source changes, is added, or is removed, the owning root is rebuilt as one semantic unit. This deliberately conservative root-level invalidation covers transitive imports, symbol tables, type analysis, diagnostics, resolution, completion, and documentation without attempting to infer a partial dependency graph that could become a second semantic authority.

Caches are never shared between roots. Invalidating one root cannot evict or mutate another root's snapshot.

## Watched files

`workspace/didChangeWatchedFiles` is accepted as a transport notification. Paths are normalized and mapped through compiler workspace ownership. Only affected roots are invalidated, then diagnostics are republished for currently open documents in those roots. The watcher event does not interpret AIDL syntax or decide semantic dependencies; the next compiler fingerprint/rebuild remains authoritative.

Dynamic workspace-folder mutation remains excluded. Roots are still fixed at launch.

## Cancellation and publication

Compiler requests may carry a `CancellationToken`. Cancellation is checked before input fingerprinting, during source hashing, after snapshot construction, and around semantic resolution. A cancelled build is not inserted into the cache.

The LSP maps request cancellation to JSON-RPC/LSP error `-32800`. Definition requests publish either one complete result or one cancellation error; no partial semantic result is emitted. Pre-cancelled requests are also rejected before a build begins.

## Progress

Expensive request paths can use an LSP `workDoneToken`. The current proof emits balanced `$/progress` begin/end notifications around `textDocument/definition`, with the terminal progress message recording `complete` or `cancelled`. Progress is protocol state only and never changes compiler semantics or scheduling.

## Lifecycle and structural load baseline

After `shutdown`, new semantic requests are rejected and `exit` retains the existing clean/unclean process-status contract. A new server instance starts with an empty compiler cache and no inherited buffers or cancellation state.

Load regressions use structural counters rather than wall-clock thresholds. Repeated definition requests over unchanged inputs must produce one compiler build followed by cache hits. This follows the M10-07 policy: deterministic work-count contracts are required gates; host-dependent latency remains observational until a controlled benchmark environment and explicit SLA exist.

## Scope boundaries

M11-03 does not expose completion, documentation, references, rename, or compiler-authorized fixes as new LSP methods; those belong to M11-04. It also does not add incremental parser semantics, cross-root caches, dynamic workspace folders, a daemon transport, or a third-party LSP framework.

Focused regressions live in `tools/test_compiler_incremental.py` and `tools/test_aidl_lsp_state.py`. They cover cache reuse, root-level transitive invalidation, saved-file watcher changes, root isolation, cancellation without cache publication, balanced progress, restart/shutdown behavior, and deterministic repeated-request load structure.

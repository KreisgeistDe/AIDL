# M6-08 LSP Evaluation

## Decision

AIDL should continue toward a **thin LSP adapter over compiler-owned semantic APIs**, not a second language implementation inside an LSP server.

M6-08 introduced a deliberately small executable proof in `tools/aidl_lsp.py`. M11-01 added compiler-owned in-memory snapshots for authoritative unsaved buffers, M11-02 added deterministic workspace discovery and isolated multi-root ownership, M11-03 added compiler-owned incremental cache/invalidation plus watcher, cancellation, progress, and lifecycle state, and M11-04 now exposes the already-existing compiler completion, documentation, usage, rename, and authorized-fix boundaries through LSP. The server is still **not** a production language server yet.

## Executable proof

Run the stdio server for one or more configured AIDL roots:

```bash
python3 -m tools.aidl_lsp path/to/project [path/to/another-project ...]
```

The proof uses Language Server Protocol JSON-RPC framing over stdin/stdout (`Content-Length` headers) and advertises only the capabilities it implements.

Supported proof capabilities:

- one or more fixed workspace/project roots selected from the server command line;
- deterministic root normalization and most-specific ownership for overlapping roots;
- safe admission of unsaved new `.aidl` files inside a configured root;
- compiler-owned per-root snapshot caching keyed by exact deterministic source fingerprints;
- deterministic root-level invalidation for saved/unsaved changes and watched-file events;
- `initialize`, `initialized`, `shutdown`, and `exit` lifecycle;
- full-text `didOpen`/`didChange` synchronization through compiler-owned state;
- compiler diagnostics from authoritative unsaved text, saved-file fallback on `didSave`, clearing on `didClose`, and refresh after watched-file invalidation;
- `textDocument/definition` from compiler resolution;
- `textDocument/completion` from compiler completion;
- `textDocument/hover` from compiler declaration/diagnostic documentation;
- `textDocument/references` from compiler-owned snapshot usage discovery;
- `textDocument/prepareRename` and `textDocument/rename` from compiler-owned conservative rename planning;
- `textDocument/codeAction` only from compiler diagnostic `allowedFixes` that the compiler-owned edit planner can map safely;
- `$/cancelRequest` mapping to compiler cancellation without partial semantic publication;
- balanced `$/progress` begin/end notifications for semantic requests carrying `workDoneToken`;
- `file://` URI ↔ filesystem-path mapping;
- LSP UTF-16 line/character ↔ compiler source-offset mapping.

Explicitly excluded from the proof:

- formatting, semantic tokens, symbols, dynamic registration, and dynamic `workspaceFolders` ownership mutation;
- incremental parser semantics, cross-root semantic caches, TCP/WebSocket transports, and daemon management;
- full protocol preservation of semantic identities, diagnostic identities, document/edit versions, and edit preconditions, which remains M11-05;
- M7 semantic diffing and every M8 `inspect`/`dependencies`/`explain` feature as LSP methods.

M11-01 provides `tools.compiler_snapshot`; M11-02 adds `tools.compiler_workspace`; M11-03 adds `tools.compiler_incremental`; M11-04 adds compiler-owned snapshot usage/rename/authorized-fix planning. Together they keep exact source text, workspace ownership, immutable semantic snapshots, cache reuse, invalidation, and edit authority inside compiler-owned APIs. See `docs/m11-compiler-snapshots.md`, `docs/m11-workspace-ownership.md`, `docs/m11-incremental-lsp-state.md`, and `docs/m11-lsp-semantic-capabilities.md`.

## Semantic boundary

The LSP layer owns protocol adaptation only:

- JSON-RPC framing and request lifecycle;
- LSP URI and UTF-16 position conversion;
- fixed launch-time root configuration;
- open-buffer full-text transport state;
- transport of watched-file notifications, request cancellation, and work-done progress;
- conversion of compiler source locations, candidates, documentation, usages, rename edits, and authorized fix edits into LSP data types.

It does **not** own AIDL naming, imports, types, diagnostics, completion, documentation, resolution, usage identity, rename eligibility, quick-fix authorization, workspace ownership, or dependency invalidation semantics.

Diagnostics are obtained from the owning cached-or-rebuilt `CompilerSnapshot.diagnostics()`. The LSP-visible diagnostic stores the compiler diagnostic payload in `Diagnostic.data`; standard LSP fields are transport projections.

Definition, completion, hover, references, rename, and code actions all select the same owning snapshot. Unresolved, ambiguous, invalid, foreign-root, collision, or unsupported-fix cases return no semantic result or a conservative request failure instead of searching another root, inspecting raw text for semantic fallback, or inventing an edit.

## Incremental and failure model

The proof is one stdio process for the configured root set. Each root owns an independent immutable snapshot cache keyed by a SHA-256 fingerprint of its exact normalized owned paths and UTF-8 source texts after overrides. Unchanged inputs reuse the same snapshot. Any change within a root invalidates that entire root's analysis, conservatively covering transitive semantic dependencies while preserving isolation between roots.

Watched-file notifications only identify affected paths/roots and invalidate compiler state; they do not interpret AIDL semantics. Cancelled requests fail with `-32800`, and a cancelled build is not inserted into the cache. Semantic requests with a work-done token emit balanced begin/end progress. After `shutdown`, new semantic requests are rejected; restart means a new process/state instance with an empty cache.

Protocol errors use normal JSON-RPC error responses for requests. Unsupported requests return method-not-found. Invalid URI/position/input mappings return invalid-params. Unexpected compiler adapter exceptions return internal-error for requests. Notification failures are suppressed rather than inventing semantic output. The process exits successfully only after the normal `shutdown` then `exit` sequence; an `exit` without prior shutdown returns a non-zero process status.

Load validation follows the M10-07 approach: deterministic structural counters are required regression signals, while wall-clock latency remains non-gating until a controlled benchmark environment and explicit SLA exist.

## Dependency decision

**No third-party LSP framework is added by M6-08 or M11-01 through M11-04.** Python's standard library remains sufficient for the current framing, URI/UTF-16 mapping, lifecycle, incremental snapshots, watcher transport, cancellation/progress, and compiler-semantic projections.

A future production server may adopt a maintained LSP protocol library after the remaining protocol-contract and packaging requirements are explicit. Any such dependency must remain transport infrastructure; compiler-owned semantic functions stay the authority.

## Recommendation for production continuation

Proceed with an LSP only as a reusable adapter package around the compiler semantic core. M11-01 through M11-04 now cover unsaved buffers, multi-root ownership, incremental state, and the existing compiler-owned editor semantics. Remaining production work includes:

1. preserve compiler diagnostic codes, semantic identities, and edit preconditions explicitly across protocol mapping;
2. choose and pin an LSP protocol dependency only if it materially reduces protocol-maintenance risk;
3. add editor smoke configurations/tests for representative clients after the server contract is stable;
4. establish controlled latency/memory benchmarks before publishing production performance promises.

The M6-08 conclusion therefore remains **feasible and recommended**; M11-04 confirms that the richer editor feature set can remain compiler-authoritative without introducing editor-local semantics.

# M10.5-04 bounded authorized-fix projection

This slice adds a Kotlin query-only projection for compiler diagnostics that already carry explicit `allowedFixes`. It matches the current Python `authorized_snapshot_fixes(...)` boundary: only `insertClause` is mapped, optional diagnostic-code filtering preserves `None` versus empty-set semantics, diagnostic/fix ordering and duplicates are retained, and missing source text, unknown fix kinds, stale/out-of-range anchors, missing header braces, or missing line endings fail closed by omission.

The Kotlin projection does **not** derive diagnostic meaning and never applies edits. Its input is the caller-owned diagnostic stream for the same exact saved or unsaved source snapshot, so existing compiler diagnostics remain the semantic authority. A JVM differential signature is pinned by a Python regression that invokes the real `create_compiler_snapshot(...)` and `authorized_snapshot_fixes(...)` helpers.

This package intentionally excludes fix application, inspect/dependencies/explain/impact, Canonical-IR hash/corpus closure, IDE/LSP integration, cache/index/service architecture, M10.5-05+, cutover/retirement, and language/schema changes. Gate 04 remains open.

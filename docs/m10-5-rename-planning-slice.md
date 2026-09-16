# M10.5-04 bounded rename-planning parity slice

This package migrates only compiler-owned **rename planning** for the already-integrated bounded Kotlin source-projection, name-resolution, definition and references surface. It does not apply edits.

`ProjectRenamePlanner` accepts one exact saved or explicit in-memory source snapshot, reuses `ProjectReferencesQuery` and `ProjectNameResolver`, and returns either the matching fail-closed status or a deterministic declaration-plus-reference text-edit plan. A ready plan carries the resolved target, the new fully qualified name, and edits sorted by source identity and offset. Every edit is checked against the old terminal declaration name before it is returned.

Python remains the migration reference/conformance implementation. `tools.compiler_snapshot_editing.plan_snapshot_rename` pins saved and unsaved behavior; saved planning is additionally checked against `tools.compiler_refactoring.rename_project_symbol(..., apply=False)`. The differential signature covers ready saved plans, explicit unsaved snapshots, ambiguity, collision, invalid identifiers and lexical failure. Common tests cover multi-root isolation, repeated runs, source-enumeration determinism and fail-closed inputs.

The identifier check is parity evidence for the Python migration oracle only; it does not create a second language authority or widen accepted syntax. Direct Core remains the permanent semantic authority.

Out of scope are filesystem edit application/preflight, authorized fixes, inspect/dependencies/explain/impact, Canonical-IR semantic hashes or corpus closure, IDE/LSP expansion, cache/index/service architecture, M10.5-05+, Kotlin default cutover, Python retirement, Native/JVM operational parity, and any language/schema change. Gate 04 remains open after this bounded slice and requires independent exact-head validation before integration.

# M10.5-04 bounded references-query parity

This package ports only the existing compiler-owned **references/usages** query boundary to Kotlin common core. Direct Core remains permanent semantic authority and Python `tools.compiler_snapshot_editing.find_snapshot_usages` remains the migration reference/conformance oracle.

`ProjectReferencesQuery` reuses `AidlSourceProjector` for lexical reference terminals and `ProjectNameResolver` for all symbol/import/FQN semantics. It owns no second resolver, workspace or reverse-reference index, cache, compiler service, adapter-local fallback, or repository-wide text-search interpretation. A query first resolves one unique declaration identity, then retains only terminals that the existing resolver maps back to that exact declaration. The declaration site itself is excluded, matching the Python usages contract.

The pinned differential matrix covers local, imported and qualified references, cross-file semantic identity, exact line/column/offset/length, explicit unsaved text shifts, lexical failure, ambiguity, deterministic repeated execution, reversed source enumeration, and isolated multi-root execution. Unknown sources, invalid offsets, lexer failures, unresolved/ambiguous targets, and uncertain project ownership fail closed. Normalization is limited to fixture source identities in place of temporary paths; statuses, semantic identities, occurrence order and ranges are exact.

Out of scope are rename planning, authorized fixes, inspect/dependencies/explain/impact, new dependency/reverse-reference indexes, cache/compiler-service architecture, IDE/LSP protocol expansion, language/schema/Core-authority changes, default Kotlin cutover, Python retirement, Native operational parity, M10.5-05+, M11-04.1, M11.5, and unrelated refactoring.

M10.5-04 remains incomplete after this slice. Rename/fixes, inspect/dependencies/explain/impact where applicable, and full Gate-04 corpus certification remain separately gated.

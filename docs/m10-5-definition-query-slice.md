# M10.5-04 bounded definition-query parity slice

This package migrates only compiler-owned **definition** lookup for the already-authorized Gate-03 resolution corpus. Direct Core remains the permanent semantic authority and Python `tools.compiler_resolution.resolve_project_reference` remains migration reference/conformance evidence.

The Kotlin common-core query reuses `AidlSourceProjector` for lexical file+offset reference extraction and `ProjectNameResolver` for all symbol/import/FQN candidate semantics. It adds no resolver, semantic index, workspace index, cache, service state, or adapter-local fallback. A resolved result projects the existing symbol identity to exact source identity, kind, line, column, and offset; invalid, unresolved, and ambiguous results never carry a target.

Differential evidence is limited to `resolution-consumer.source`, `resolution-provider-a.source`, and `resolution-provider-b.source`. In-memory cases append reference-bearing body clauses to the consumer text without changing its module/import/declaration graph; this proves the query can consume explicit unsaved text without introducing workspace/service architecture. Multi-root ownership/routing remains outside this common-core slice.

Only transport normalization is permitted in the Python-versus-Kotlin comparison: temporary Python paths are mapped to fixture source IDs, path separators may be normalized, and Kotlin enum spelling is rendered lowercase. Status, reference text, FQN, kind, line, column, offset, ambiguity, and target source identity remain exact.

M10.5-04 stays open. Completion, documentation, references, rename/fixes, inspect/dependencies/explain/impact, semantic hashes, default-compiler cutover, M10.5-05+, M11-04.1, M11.5, Native operational parity, and IDE/LSP protocol changes remain deferred.

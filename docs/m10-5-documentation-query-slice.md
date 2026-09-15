# M10.5-04 bounded documentation-query parity

This slice ports only the existing compiler-owned documentation query boundary to Kotlin. Python `tools.compiler_documentation.document_project_source` remains the conformance oracle and direct Core remains semantic authority.

The Kotlin query reuses `AidlSourceProjector` and `ProjectNameResolver`; it owns no independent parser, resolver, index, cache, workspace, language rule, or schema. The pinned differential matrix covers saved local/imported/qualified declarations, unresolved and ambiguous references, invalid offsets, in-memory location shifts, lexical failure, deterministic repeatability, and unknown/non-word fail-closed contexts.

Out of scope are references, rename, fixes, inspect/dependency/explain/impact graph queries, cache/index/compiler-service architecture, IDE/LSP expansion, M10.5-05+, Native CLI/default-compiler cutover, Python retirement, language/schema changes, and unrelated refactoring. This slice does not complete Gate 04.

Focused evidence is provided by `tools/test_m10_5_kotlin_documentation_query.py` and `DocumentationQueryDifferentialParityTest`; the Python oracle is registered in the required compiler regressions.

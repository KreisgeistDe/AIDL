# M16.5 evaluation-only candidate → current compiler projection

Status: **experimental recovery prerequisite only**. Project base: `c265046360ac8ff457c7018c7727444fb27f96ba` (`main`). This package closes only the candidate-work-product → unchanged-production-compiler evidence gap. It does not implement E8, execute a model or benchmark, compare before/after runs, select a preferred syntax, start E9, or change accepted AIDL behavior.

## Boundary and identity

Production grammar, parser/lexer, AST, Canonical IR, diagnostics, formatter/migrator, IDE/LSP, runtime/generator, compatibility/support/conformance, the frozen M16 corpus/baseline, `tools/m16_evaluation_runner.py`, and project `.ai/**` remain unchanged.

The projection contract is explicit and fail closed:

- ID `urn:aidl:evaluation:m16.5-candidate-current-projection`
- version `1`
- fingerprint `sha256:a99667aecc90877da362f51fdf4fb7f5775b2f3ceb5a2911871f73443f52136c`
- E3 candidate `m16.5-e3-candidate-v2` / `sha256:367b920826a5c85ced83e58ddaec959e8539064e4f04e49486655c54bf695d85`
- E4 introspection `0.2.0-e4` / `sha256:68465a548d3322af3ae2d14df018fde1f08cdd161ce864f648f96a32a20dfdf2`
- E5 current `m16.5-e5-current-v1` / `sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822`
- E5 candidate `m16.5-e5-candidate-v2` / `sha256:b30abd7f3534e7792c041ecf1e67f22c264be05712324a36096056dde5cebaf5`

Any stale or mismatched tuple fails before projection. There is no latest-version selection, syntax sniffing, task-ID switch, benchmark-answer lookup, fallback parser, or implicit migration state.

## Mechanically derived inverse

`tools/m16_5_candidate_projection.py` adds no second row or syntax table. Candidate anchors and semantic facts come from E5. For each E5 candidate match, a generic regex-witness renderer derives the current spelling from the paired E5 **current regex** plus candidate/E5 fact bindings. The witness must full-match that exact current regex. E3 normalization rows and E5 fact-complete rows must be the same set.

The inverse then copies untouched bytes, compares complete E5 candidate/current fact tuples, forward-migrates the projected current text with E5 again, and requires exact equality with `Formatter(candidate)`. Missing or duplicated single-cardinality facts, incomplete candidate anchors, overlapping edits, unsupported E3-only constructs, stale identities, legacy spelling in candidate context, fact mismatch, or non-lossless round trip fail closed.

Repeatable projection sources preserve order and multiplicity; they are never sorted.

## Production compiler oracle

`project_worktree(...)` stages a copy of the candidate worktree, projects every UTF-8 `.aidl` file, and invokes the unchanged repository compiler entry point for both `aidl check <projected> --format json` and `aidl ir <projected> --format json`. The requested output directory is published only if both commands report `ok=true` with matching success exit codes. Compiler rejection remains rejection and no output is published.

The positive integration fixture starts from the CI-certified Petstore M4 slice and changes only Entity-field and topic dead-letter spellings to candidate form. The test compares the projected result with a separately authored current counterpart using E5 facts and Canonical IR (excluding source-map path differences), including the semantic hash. A negative worktree preserves production compiler rejection. Known parser/tooling gaps are not repaired or special-cased.

## Evidence scope

`fixtures/m16-5/evaluation-candidate-projection-cases.json` contains independently authored Candidate/Current examples for all nine E5 normalization rows plus reordered/repeated projection sources and fail-closed cases. `tools/test_m16_5_candidate_projection.py` covers exact identities, all rows, stale contexts, missing/ambiguous facts, unsupported constructs, no version sniffing, compiler acceptance/IR equality, compiler rejection, and absence of a duplicate local syntax table. The companion determinism test runs every independent candidate projection twice and requires byte-identical/result-identical output.

Repository GitHub Actions are the authoritative full-checkout regression gate. This prerequisite creates no empirical M16/E8 evidence; a separately authorized E8 runner may consume it later while keeping the frozen inputs and production authority unchanged.

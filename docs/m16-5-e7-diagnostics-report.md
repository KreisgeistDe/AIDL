# M16.5 E7 — isolated schema-driven diagnostics prototype

Status: **experimental E7 evidence only**. Project base: `6eaf5691c4611fb1fbff198f0899079793ab4aac` (`main`). This package does not change accepted AIDL syntax, lexer/parser acceptance, AST or Canonical-IR authority, production formatter/migrator behavior, production IntelliJ/LSP/completion behavior, production diagnostics rollout, compatibility/support/conformance, generators/runtime, or project `.ai/**`. E5 candidate spellings remain non-production prototype notation.

## Authority boundary

`tools/m16_5_e7_diagnostics.py` is a transport-neutral diagnostics consumer. Current structural facts come only from `CompilerSchemaService` in the integrated E4 prototype and every request carries the exact immutable E4 schema tuple:

- `urn:aidl:schema:meta:m16.5-e4-introspection`
- `0.1.0-e4`
- `sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542`

There is no E7 declaration/slot/value/modifier/sublanguage grammar table, latest-version selector, syntax sniffing, or fallback. Unknown/stale E4 metadata is a fail-closed `AIDL-S008` context error. Unmodeled source surfaces are not reconstructed client-side.

The existing production IntelliJ diagnostics path remains untouched: it shells out to compiler `aidl check --format json` and presents compiler-owned code, phase, severity, message and source location. E7 neither imports nor changes that adapter.

## Structural diagnostics

E7 renders only schema-owned structural failures whose facts E4 actually exports:

- `AIDL-S003` for an unknown body slot relative to the exact declaration metadata;
- `AIDL-S004` for a wrong value when E4 exports a closed value set;
- `AIDL-S005` for an invalid exported modifier or incompatible exported nested schema;
- `AIDL-S008` for stale/unknown schema context rather than guessing another schema.

Representative fixture coverage includes App unknown slots, Core/Entity field modifiers, Backend/Service nesting, and Sync closed mode values. For open/non-exported value vocabularies E7 returns `value-validation-not-exported` rather than interpreting grammar itself.

`profileProperty`, `uiStatement`, and `testStatement` are queried through E4. Their structural descriptors are closed, but E4 does not export the concrete vocabularies, so E7 returns `closed-vocabulary-not-exported`; it never invents a profile/UI/test keyword.

## Source localization and ordering

Every E7 diagnostic receives an explicit source span and deterministically derives 1-based line/column data without reparsing source. E7 can order **only its own** diagnostics by source offset, phase, severity/code/message tie-breakers. It never accepts a production diagnostic list and therefore cannot reorder or recode pre-existing compiler diagnostics.

The diagnostic model exposes `compatibility_class=None` and `migration_authorized=false`. Structural presentation cannot classify M7 compatibility or authorize a write.

## Explicit E5 migration/deprecation context

Migration diagnostics require all E5 identities explicitly: old/target/source schema IDs, versions, schema fingerprints, exact source fingerprint, plus an explicit prototype language state (`legacy`, `coexistence`, or `target`). Nothing is inferred from source text.

For old source with a fact-complete E5/E3 mapping:

- explicit `legacy` state emits no migration diagnostic merely because the spelling is old;
- explicit `coexistence` state may render E2 `AIDL-S006` with the exact E5 dry-run replacement;
- explicit `target` state may render E2 `AIDL-S007` with the exact E5 dry-run replacement.

These are prototype state projections, not adoption claims. The replacement is informational only; `migration_authorized` remains false. Target-version source under an explicit target context produces no legacy-spelling diagnostic and is never reinterpreted as current accepted syntax.

E5 failures retain their `AIDL-S###` code and source offset. Multi-source projection fact loss therefore remains `AIDL-S004`. Edits not in `MigrationPlan.e3_replayed_rows` remain explicitly unavailable, covering the documented incomplete index-direction, dead-letter threshold, schedule-lease, Sync-outbox, and other incomplete mappings. The schedule tooling-parser gap is not repaired or promoted.

## Equivalent-invalid semantic intent

E7 does not create semantic diagnostics. `CompilerSemanticIntent` represents an already compiler-owned semantic diagnostic. `equivalent_semantic_intent(...)` projects that same code/phase/severity/message onto old and candidate source locations **only** when:

1. the exact old E5 context validates;
2. E5 produces a unique dry-run edit at the source location;
3. the row is in E5's E3-replayed fact-complete set;
4. the supplied candidate snapshot is byte-for-byte the E5 dry-run result; and
5. E5 provides the deterministic relocation for that anchor.

The resulting old/candidate projections preserve the same semantic intent while retaining distinct source contexts/ranges. Incomplete mappings return an unavailable result rather than manufacturing semantic equivalence. M7 remains the sole compatibility-classification authority.

## Focused fixtures/tests

`fixtures/m16-5/e7-diagnostics-cases.json` and `tools/test_m16_5_e7_diagnostics.py` cover:

- the exact E4 tuple and fail-closed stale/unknown metadata;
- representative App/Core/Backend/Sync invalid structural cases;
- valid exported facts producing no E7 diagnostic;
- generic profile/UI/test vocabulary closure;
- deterministic source localization and E7-only ordering;
- compatibility/write non-authority;
- explicit legacy/coexistence/target E5 context separation;
- no latest/fallback/source sniffing;
- compiler-owned semantic-intent consistency for fact-complete client/projection mappings;
- exact E5 target-snapshot gating;
- incomplete E3/E5 mappings and multi-source fact loss remaining fail closed;
- absence of a second E7 language schema or production diagnostics import.

Local syntax validation in the isolated workspace:

```text
python3 -m compileall -q tools/m16_5_e7_diagnostics.py tools/test_m16_5_e7_diagnostics.py
# exit 0
```

The container could not resolve `github.com`, so it could not clone the public project for an exact local E3–E7 regression run. The project PR's normal GitHub Actions validation is therefore the authoritative exact-head regression gate and must pass before E7 completion is reported.

## Known gaps and later boundary

E4 remains representative rather than full-corpus and still lacks concrete profile/UI/test vocabularies. E5 remains bounded and has incomplete E3 fact shapes. E7 therefore cannot diagnose every declaration/value/profile construct, prove full invalid-source parity, adopt a migration lifecycle, classify compatibility, or replace production diagnostics.

E8 evaluation, E9 language-version implementation, production diagnostics rollout, candidate-language adoption, and unrelated milestone work remain out of scope.

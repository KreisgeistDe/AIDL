# M16.5 E6 — isolated IDE/completion consumer prototype

Status: **experimental E6 evidence only**. Project base: `77fa491fa780a833291b1155deaa280524a40a77` (`main`). E4 and E5 are integrated dependencies at this base. This package does not change accepted AIDL syntax, lexer/parser acceptance, AST or Canonical-IR authority, production formatter/migrator behavior, production IntelliJ/LSP/completion behavior, diagnostics rollout, compatibility/support/conformance, generators/runtime, or project `.ai/**`. E5 candidate spellings remain non-production prototype notation.

## Existing IDE boundary

The current IntelliJ completion path already treats the compiler as authority: `AidlCompilerCompletionAdapter` shells out to `aidl complete ... --format json`, parses the compiler envelope, and the contributor only presents returned candidates. E6 does **not** wire into or modify that production path. The experiment remains a transport-neutral Python consumer so the E4/E5 contracts can be tested without promoting prototype notation into the IDE.

## E4 compiler-owned construction metadata

`tools/m16_5_e6_completion.py` consumes `CompilerSchemaService` from `tools/m16_5_e4_introspection.py` through the exact immutable tuple:

- schema ID: `urn:aidl:schema:meta:m16.5-e4-introspection`
- semantic version: `0.1.0-e4`
- fingerprint: `sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542`

Every current-language request carries `CurrentCompletionContext(schema_ref=...)`; there is no latest-version selector, fallback, syntax sniffing, or client-side schema reconstruction. Unknown declaration, value, modifier, sublanguage, stale version, or fingerprint failures come from the E4 service and remain fail closed.

The E6 consumer has no declaration/slot/value/modifier/row grammar tables. It obtains declaration starters, header arguments, body slots, value shapes, modifiers, nesting and documentation by querying E4. The focused test source also asserts that representative E4 vocabulary and E5 row IDs are absent from the E6 implementation.

## Representative completion evidence

Fixture `fixtures/m16-5/e6-completion-cases.json` and `tools/test_m16_5_e6_completion.py` exercise App/Core/Backend/Sync without hard-coding those shapes in the consumer:

- **App:** declaration starter plus ordered `profile/system/frontend/api/defaultDeployment/compatibility` body metadata;
- **Core / Entity:** declaration starter, keywordless field metadata without inventing an insertion template, `index`/`invariant` body metadata, and the compiler-owned field modifier set including valued modifiers;
- **Backend / Service:** declaration starter, ordered service slots, and `reliability -> profileProperty` nested-schema discovery;
- **Sync:** declaration starter, `for` header argument with expected `type` value shape, ordered body slots, and closed `sync-mode` values supplied by E4.

Insertion text is emitted only when E4 exposes visible tokens or a closed value. For a keywordless Entity field the consumer returns name/value-shape metadata and `insert_text=None` rather than inventing punctuation or a snippet that E4 did not export.

All representative E4 declaration metadata currently has `semantic_order=preserve`; E6 therefore returns the compiler order unchanged and does not sort. Client-owned ranking would only be valid where compiler metadata explicitly says `unordered`.

## Generic profile/UI/test sublanguages

E4 exposes `profileProperty`, `uiStatement`, and `testStatement` as recursive/closed structural schemas with compiler/profile vocabulary authority, but intentionally does not export the concrete profile/UI/test keyword vocabularies in this bounded prototype. E6 therefore exposes their structural alternatives for discovery while returning explicit `closed-vocabulary-not-exported` for vocabulary completion. It never invents unknown profile, UI, or test keywords and never treats generic identifiers as open language extensions.

This is a deliberate coverage result rather than a workaround: production completion cannot claim complete generic-sublanguage vocabulary until the compiler/profile authorities actually export it.

## Explicit E5 migration context

Candidate suggestions use a separate `E5MigrationCompletionContext` and require all caller-supplied identities to match E5 exactly:

- old schema `urn:aidl:schema:language:m16.5-e5-current`, version `m16.5-e5-current-v1`, fingerprint `sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822`;
- target schema `urn:aidl:schema:language:m16.5-e5-candidate`, version `m16.5-e5-candidate-v1`, fingerprint `sha256:c702262d2f5374d8eda54a028923d00d7d21e45d3980c62f32d472392ccc8c30`;
- exact source schema/version/fingerprint plus exact source-content fingerprint.

E6 never infers that context from source text. Current E4 completion and E5 target completion are separate APIs and response contexts, so accepted current syntax and candidate notation are never implicitly mixed.

For an explicit migration request, E6 calls E5 `plan_migration(...)` and presents only the exact replacement already emitted by E5's dry-run edit plan. It does not reconstruct candidate syntax from E5 regexes or from a local mapping. A target-version no-op yields no candidate rather than being reinterpreted as current syntax.

## Fail-closed E5 gaps

E6 deliberately narrows candidate presentation beyond merely obtaining an E5 edit. The replacement is exposed only when its row ID is also present in E5 `MigrationPlan.e3_replayed_rows`, i.e. when E5 proved that the E3 candidate shape can carry the bounded facts without a client translation. This keeps the documented incomplete E3 shapes unavailable instead of converting them into completion semantics.

Focused fixtures prove:

- multi-source projection remains unavailable through E5 `AIDL-S004` fact-loss protection;
- explicit index, dead-letter/schedule/Sync-style non-replayed target shapes remain unavailable rather than invented;
- the narrowly documented schedule tooling-parser gap is therefore not promoted into completion behavior;
- unmodeled source produces no candidate;
- stale or mismatched E5 IDs/versions/fingerprints fail before migration planning.

E6 does not authorize migration writes. It only presents a dry-run replacement that remains owned by E5. Compatibility class, write authorization, rollback/application, source maps, Canonical-IR meaning, reference resolution, typing and profile legality stay with compiler/M7 authorities.

## Focused and regression validation

Local isolated validation against the integrated E3/E4/E5 prototype copies used by this experiment:

```text
python3 -m compileall -q tools/m16_5_e6_completion.py tools/test_m16_5_e6_completion.py
# exit 0

python3 -m unittest -v tools.test_m16_5_e6_completion
# 15 tests, OK

python3 -m unittest -q \
  tools.test_m16_5_e6_completion \
  tools.test_m16_5_e4_introspection \
  tools.test_m16_5_e5_migration \
  tools.test_m16_5_e3_prototype
# 49 tests, OK
```

An earlier scratch-workspace E3 regression attempt used a mismatched copied E3 module/test snapshot and failed during test import; after replacing that scratch copy with the integrated E3 prototype plus fixture, the combined 49-test run above passed. This was a local workspace assembly error, not a project-source regression.

Repository-wide exact-head CI remains the authoritative project regression gate and must be recorded from the PR before E6 completion is claimed.

## Known coverage gaps and later boundary

E4 still covers only representative App/Core/Backend/Sync declaration metadata, not the complete declaration corpus, and it does not export full profile/UI/test vocabularies. E5 remains a bounded migration experiment with multi-source projection and incomplete E3-shape gaps. E6 therefore cannot provide complete production completion, candidate formatting, reference/typing semantics, profile legality, or migration authorization.

The experiment supports the direction "IDE consumes compiler-owned construction metadata" while showing the missing compiler-exported vocabulary/coverage that production adoption would require. E7 diagnostics, E8 evaluation, E9 language-version implementation, and any production IDE rollout remain out of scope and require separate authorization.

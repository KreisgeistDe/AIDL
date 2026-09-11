# M10.1 Compatibility Bridge

## Status and authority

This implementation is the executable bridge behind the existing Python parser for the frozen M10.1 language surface. It does not change accepted source syntax and it does not define a second language schema. `spec/language-surface-v1.json` remains the only declaration/body/modifier construction contract consumed by the bridge; `docs/06-grammar.md` remains the currently accepted legacy source grammar.

The bridge lives in `tools/compiler_language_surface.py`. It projects parser `Node` values into immutable canonical semantic records for declarations, name policy, header arguments, body slots, type/reference facts, modifier calls and literal-versus-expression modes. Stable semantic JSON and SHA-256 hashes deliberately exclude parser locations and source whitespace.

## Implemented normalization

The bridge normalizes these representative legacy surfaces:

- `migration ... from ... to ...`, `client ... for ...`, `consumer ... on ... from ...` and `projection ... from ... into ...` into contract-owned named `HeaderArg` facts;
- unprefixed `entity` fields into the `field` `BodySlot`, including `T?`, list/reference type structure and contract-declared field modifiers;
- `opaque` into canonical `alias` identity plus an explicit opacity semantic fact while preserving its aliased type;
- `ref` forms and resolver-backed projections such as `Pet.id` into structured target/projection/resolved-type facts;
- enum cases into first-class `case` slots, including optional wire literals;
- `app` profile/version clauses into nested contract body-slot facts;
- `@publicReason(...)` and other contract-declared annotations into target/arity/value-mode checked `ModifierCall` values;
- query `read` clauses as expression-valued body slots while migration header versions remain literal-valued facts.

Normalization fails closed with stable `AIDL-N###` diagnostics for unknown declaration kinds, missing/forbidden names, missing required header facts, malformed/duplicate/overflow body slots, invalid modifier target/arity, unsupported profile shapes and unresolved reference projections that lack resolver evidence. Legacy clauses or modifier tails not yet represented by the frozen contract are retained as explicit warning diagnostics rather than silently treated as canonical.

## Production integration slice

`tools/compiler_language_surface_integration.py` is the first production adapter over the real `CompilerAnalysis`/`CompilerProject` path. It reuses the existing typed parser nodes, compiler symbol/import resolution and Core typechecker parser/checker instead of reproducing any of those semantics. The integrated declaration set is intentionally limited to `alias`/`opaque`, `entity`, `enum`, `migration`, `client`, `consumer` and `projection`, because those surfaces are already representable losslessly by the frozen contract.

For entity field projections, the adapter first uses the bridge to remove parser-token whitespace from the already frozen type surface, then feeds that normalized spelling through the existing Core `parse_type`/type-check logic and project resolver. `Pet.id?` is therefore represented as optional `TypeRef(kind=reference,target=Pet,projection=id,resolved_type=uuid)` only when the compiler project resolves exactly one `Pet` entity and that entity has an `id` field whose type is accepted by the existing Core type parser. Missing, ambiguous or untyped projection evidence produces stable `AIDL-N012` and keeps the production surface non-OK. A dotted `ref` is first tested as a complete nominal entity reference before any final segment is interpreted as a projection, preserving existing qualified-name behavior.

The existing compiler-owned `summary` path is the first downstream consumer. Its in-memory `ProjectSummary` carries the production-slice semantic hash, declaration count, diagnostic codes and `ok` state. `ProjectSummary.to_json()` deliberately keeps the existing CLI JSON contract unchanged; publishing M10.1 evidence through CLI JSON would require an explicit CLI schema/version change and is outside this slice. The production hash is versioned as `aidl.m10.1-production/v1`, is computed only from normalized semantic records, and excludes source paths/spans/whitespace. Canonical IR shape is unchanged.

The production adapter does not suppress Core typechecker failures. It reuses the existing checker on the normalized frozen type spelling so parser token spacing cannot hide a semantic mismatch. In particular, legacy `ref Pet.id` remains fail-closed because the current Core checker resolves the dotted `ref` as a nominal entity reference; the bridge may derive projection evidence, but the production surface stays non-OK until the Core resolver/typechecker gains an explicit projection-aware path without weakening ordinary qualified-name resolution. This is deliberate parity evidence rather than a heuristic compatibility exception.

## Semantic hash and equivalence

`Declaration.semantic_json()` and `Document.semantic_json()` use deterministic sorted-key compact JSON. Their SHA-256 hashes are semantic-normalization fingerprints, not source hashes: source spans, whitespace and parser-node shapes are excluded. Tests prove that the legacy migration spelling and an independently constructed canonical declaration with the same named facts produce the same normalized declaration hash.

The bridge hash is intentionally versioned through `aidl.m10.1-normalized/v1` at document scope. The production integration adds its own aggregate envelope version `aidl.m10.1-production/v1`. Changing semantic normalization rules requires an explicit version change; callers must not use either hash as a source-compatibility substitute.

## Formatter and migrator split

`LanguageSurfaceBridge.format_legacy()` is same-version canonicalization for the supported representative legacy forms. It emits the current accepted source version and is idempotence-tested.

`LanguageSurfaceBridge.migrate_to_canonical_preview()` is a separate, explicit cross-version prototype. It emits only target shapes that are directly representable by the frozen contract. It is never called by the same-version formatter. Where the contract is not yet sufficient for lossless target syntax, migration fails explicitly instead of inventing syntax; opaque-alias opacity and parameterized operation signatures are current examples.

The canonical preview is evidence for the future versioned parser/migrator package, not a claim that the production parser accepts the preview today.

## Regression coverage

`tools/test_m10_1_compatibility_bridge.py` covers contract authority, relationship headers, opaque aliases, reference projections, type optionality versus body cardinality, app profiles, enum cases, `@publicReason`, literal/expression separation, deterministic semantic hashes, duplicate/occurrence diagnostics, resolver-required projections, same-version formatter idempotence and the explicit formatter/migrator boundary.

`tools/test_m10_1_production_integration.py` adds parity evidence over real compiler analysis: compiler-backed `Pet.id?` projection/type evidence, optionality preservation, source-location/whitespace-independent production hashes, compiler-internal summary consumption, stable unresolved-projection diagnostics, legacy `ref Pet.id` fail-closed behavior, Canonical IR semantic-hash/diagnostic location parity, legacy/canonical semantic equivalence, and continued formatter/migrator separation.

## Deliberately pending legacy surfaces

The production slice does not yet normalize every grammar family. Operation parameter schemas and generic constraints, view selections, indexes/invariants, app/auth/profile property mini-languages, query/mutation bodies, broader messaging/topic/queue bodies, workflow/saga/task internals, resource/deployment/sync/UI/test mini-languages, the complete modifier vocabulary, and project-wide expression/type facts remain pending. Parser recovery/source-token fidelity also remains owned by the existing parser.

The generic bridge can model some of those representative shapes, but they are not wired into the production adapter until existing compiler facts and the frozen contract can represent them losslessly. Unsupported areas therefore remain outside the integrated declaration set rather than being guessed into canonical semantics.

## Next sequential M10.1 step

The next dependency-ready package is the narrow Core typechecker/resolver parity step for frozen legacy reference projections and modifier/value-mode evidence: make `ref Pet.id` distinguish a resolvable qualified entity from an entity-field projection using the same project resolver, then widen production normalization only for contract-backed query/mutation/app surfaces that already have lossless compiler facts. Differential evidence must show unchanged diagnostics/IR for existing sources and identical normalized semantics for supported legacy/canonical representations.

M10.5-03 Kotlin front-end/IR slices remain blocked until the M10.1 compatibility path is complete and the frozen semantics have executable parity evidence. This package does not start Kotlin compiler work and does not perform M16.5 syntax adoption.

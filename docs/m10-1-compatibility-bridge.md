# M10.1 Compatibility Bridge

## Status and authority

This implementation is the first executable bridge behind the existing Python parser for the frozen M10.1 language surface. It does not change accepted source syntax and it does not define a second language schema. `spec/language-surface-v1.json` remains the only declaration/body/modifier construction contract consumed by the bridge; `docs/06-grammar.md` remains the currently accepted legacy source grammar.

The bridge lives in `tools/compiler_language_surface.py`. It projects parser `Node` values into immutable canonical semantic records for declarations, name policy, header arguments, body slots, type/reference facts, modifier calls and literal-versus-expression modes. Stable semantic JSON and SHA-256 hashes deliberately exclude parser locations and source whitespace.

## Implemented normalization

The current package normalizes these representative legacy surfaces:

- `migration ... from ... to ...`, `client ... for ...`, `consumer ... on ... from ...` and `projection ... from ... into ...` into contract-owned named `HeaderArg` facts;
- unprefixed `entity` fields into the `field` `BodySlot`, including `T?`, list/reference type structure and contract-declared field modifiers;
- `opaque` into canonical `alias` identity plus an explicit opacity semantic fact while preserving its aliased type;
- `ref` forms and resolver-backed projections such as `Pet.id` into structured target/projection/resolved-type facts;
- enum cases into first-class `case` slots, including optional wire literals;
- `app` profile/version clauses into nested contract body-slot facts;
- `@publicReason(...)` and other contract-declared annotations into target/arity/value-mode checked `ModifierCall` values;
- query `read` clauses as expression-valued body slots while migration header versions remain literal-valued facts.

Normalization fails closed with stable `AIDL-N###` diagnostics for unknown declaration kinds, missing/forbidden names, missing required header facts, malformed/duplicate/overflow body slots, invalid modifier target/arity, unsupported profile shapes and unresolved reference projections that lack resolver evidence. Legacy clauses or modifier tails not yet represented by the frozen contract are retained as explicit warning diagnostics rather than silently treated as canonical.

## Semantic hash and equivalence

`Declaration.semantic_json()` and `Document.semantic_json()` use deterministic sorted-key compact JSON. Their SHA-256 hashes are semantic-normalization fingerprints, not source hashes: source spans, whitespace and parser-node shapes are excluded. Tests prove that the legacy migration spelling and an independently constructed canonical declaration with the same named facts produce the same normalized declaration hash.

The hash is intentionally versioned through `aidl.m10.1-normalized/v1` at document scope. Changing semantic normalization rules requires an explicit version change; callers must not use the hash as a source-compatibility substitute.

## Formatter and migrator split

`LanguageSurfaceBridge.format_legacy()` is same-version canonicalization for the supported representative legacy forms. It emits the current accepted source version and is idempotence-tested.

`LanguageSurfaceBridge.migrate_to_canonical_preview()` is a separate, explicit cross-version prototype. It emits only target shapes that are directly representable by the frozen contract. It is never called by the same-version formatter. Where the contract is not yet sufficient for lossless target syntax, migration fails explicitly instead of inventing syntax; opaque-alias opacity and parameterized operation signatures are current examples.

The canonical preview is evidence for the future versioned parser/migrator package, not a claim that the production parser accepts the preview today.

## Regression coverage

`tools/test_m10_1_compatibility_bridge.py` covers contract authority, relationship headers, opaque aliases, reference projections, type optionality versus body cardinality, app profiles, enum cases, `@publicReason`, literal/expression separation, deterministic semantic hashes, duplicate/occurrence diagnostics, resolver-required projections, same-version formatter idempotence and the explicit formatter/migrator boundary.

## Deliberately pending legacy surfaces

This package does not yet normalize every grammar family. In particular, operation parameter schemas and generic constraints, view selections, indexes/invariants, most profile-property mini-languages, messaging/topic/queue clauses beyond the frozen representative headers, workflow/saga/task internals, resource/deployment/sync/UI/test mini-languages, full modifier vocabulary, and resolver-derived reference facts across complete projects remain pending. Parser recovery/source-token fidelity also remains owned by the existing parser.

The bridge therefore emits warnings for unsupported body clauses and refuses canonical migration output when the frozen contract cannot represent a fact without invention.

## Next sequential M10.1 step

The next dependency-ready package is the parser/AST/resolver/typechecker integration step: feed real project resolution/type information into the canonical bridge, expand normalization only where `spec/language-surface-v1.json` already has authoritative facts, and route compiler-owned consumers through the canonical model while preserving current diagnostics and IR parity. Contract gaps discovered during that work must be resolved as explicit M10.1 language-design changes before implementation.

M10.5-03 Kotlin front-end/IR slices remain blocked until the M10.1 compatibility path is complete and the frozen semantics have executable parity evidence. This package does not start Kotlin compiler work and does not perform M16.5 syntax adoption.

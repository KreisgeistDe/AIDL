# M10.1 Compatibility Bridge

## Status and authority

This implementation is the executable bridge behind the existing Python parser for the frozen M10.1 language surface. It does not change accepted source syntax and it does not define a second language schema. `spec/language-surface-v1.json` remains the only declaration/body/modifier construction contract consumed by the bridge; `docs/06-grammar.md` remains the currently accepted legacy source grammar.

The bridge lives in `tools/compiler_language_surface.py`. It projects parser `Node` values into immutable canonical semantic records for declarations, name policy, header arguments, body slots, type/reference facts, modifier calls and literal-versus-expression modes. Stable semantic JSON and SHA-256 hashes deliberately exclude parser locations and source whitespace.

## Implemented normalization

The bridge normalizes these representative legacy surfaces:

- declaration-specific relationship headers into contract-owned named `HeaderArg` facts;
- unprefixed `entity` fields into the `field` `BodySlot`, including `T?`, list/reference structure and contract-declared field modifiers;
- `opaque` into canonical `alias` identity plus an explicit opacity fact;
- `ref` forms and resolver-backed projections such as `Pet.id` into structured target/projection/resolved-type facts;
- enum cases into first-class `case` slots;
- `app` profile/version clauses into nested contract body-slot facts;
- `@publicReason(...)` and other contract-declared annotations into target/arity/value-mode checked `ModifierCall` values;
- query `read` clauses as expression-valued body slots while migration versions remain literal-valued facts.

Normalization fails closed with stable `AIDL-N###` diagnostics for unsupported or ambiguous frozen facts rather than silently inventing canonical meaning.

## Core reference-projection parity

`tools/compiler_typecheck.py` now owns deterministic resolution for legacy `ref` types. Resolution follows one rule: an exact entity resolution wins first. Only when the complete dotted reference resolves to zero entities may the final segment be interpreted as an entity-field projection. Ambiguous exact entity names, ambiguous projection targets, duplicate projected fields and non-parseable projected field types fail closed.

A successful projection produces separate compiler-owned evidence for `target`, `projection` and `projected_type`. Nullable syntax remains an outer `TypeRef(nullable, ...)` concern, so `ref Pet.id?` resolves the same projection as `ref Pet.id` while preserving optionality independently. Legitimate qualified references such as `ref demo.Pet` remain nominal references and are not reinterpreted as `demo`.`Pet` projections.

The production adapter in `tools/compiler_language_surface_integration.py` consumes that Core resolver/typechecker evidence instead of implementing another naming rule. Missing or ambiguous projections produce `AIDL-N012` plus the existing Core `AIDL-T001` where applicable. Qualified nominal references are supplied to the bridge as target-only resolver evidence, preventing the generic bridge's dotted-reference fallback from changing their meaning.

## Lossless query/mutation/app integration

The production normalization envelope is versioned as `aidl.m10.1-production/v2`. The always-integrated lossless set remains `alias`/`opaque`, `entity`, `enum`, `migration`, `client`, `consumer` and `projection`. `query`, `mutation` and `app` are admitted only when the existing parser facts and frozen contract cover the complete represented shape without approximation.

Current lossless additions are parameterless query/mutation result types, query `read` expression slots, `app` profile/version slots and contract-declared annotations. Parameterized operations and query/mutation/app bodies containing unsupported clauses remain outside the normalized declaration set and emit `AIDL-N013`; they are not hashed as if complete.

Modifier target and arity validation remains owned by `LanguageSurfaceBridge` through `spec/language-surface-v1.json`. Production integration additionally keeps lexical value-mode evidence from the existing parser AST: a contract modifier requiring literal arguments fails with `AIDL-N014` when its source argument is expression-like instead of a literal. No second modifier inventory is introduced.

The compiler-owned `summary` path continues to consume the production semantic hash and diagnostic state in memory. `ProjectSummary.to_json()` deliberately keeps the existing CLI JSON contract unchanged. Canonical IR shape is also unchanged.

## Semantic hash and equivalence

`Declaration.semantic_json()` and `Document.semantic_json()` use deterministic sorted-key compact JSON. Semantic hashes exclude source spans, paths and whitespace. The bridge document hash remains `aidl.m10.1-normalized/v1`; the production aggregate is now `aidl.m10.1-production/v2` because the integrated semantic set expanded.

Regression coverage proves source-location/whitespace independence, representative legacy/canonical semantic equivalence, stable diagnostics and unchanged Canonical IR semantic hashes for equivalent sources.

## Formatter and migrator split

`LanguageSurfaceBridge.format_legacy()` remains same-version canonicalization. `LanguageSurfaceBridge.migrate_to_canonical_preview()` remains a separate explicit cross-version prototype. Neither Core reference resolution nor production normalization invokes language-version migration implicitly.

## Deliberately pending legacy surfaces

The production path still does not losslessly normalize operation parameter schemas/generic constraints, view selections, indexes/invariants, broader app/auth/profile property mini-languages, unsupported query/mutation clauses, messaging/topic/queue bodies, workflow/saga/task internals, resource/deployment/sync/UI/test mini-languages, the complete modifier vocabulary, or project-wide expression/type semantics. Parser recovery and token fidelity remain owned by the existing parser.

These surfaces must stay explicit (`AIDL-N010`/`AIDL-N013` or existing compiler diagnostics) until both frozen-contract representation and compiler-owned evidence are lossless.

## Next sequential M10.1 step

The next dependency-ready package is a narrow operation-signature and remaining contract-backed body/modifier parity slice: model parameter facts only if `spec/language-surface-v1.json` is extended or already proves a lossless canonical representation, then widen query/mutation/app normalization without altering CLI or Canonical IR contracts. Unsupported mini-languages remain out of scope rather than being approximated.

M10.5-03 Kotlin front-end/AST/IR slices remain blocked until the M10.1 compatibility path is complete. This package does not start Kotlin compiler work and does not perform M16.5 syntax adoption.

# M10.1 Compatibility Bridge

## Status and authority

This implementation is the executable bridge behind the existing Python parser for the frozen M10.1 language surface. It does not change accepted source syntax and it does not define a second language schema. `spec/language-surface-v1.json` remains the only declaration/body/modifier construction contract consumed by the bridge; `docs/06-grammar.md` remains the currently accepted legacy source grammar.

The base bridge lives in `tools/compiler_language_surface.py`. It projects parser `Node` values into immutable canonical semantic records for declarations, name policy, header arguments, operation parameters, body slots, type/reference facts and modifier calls. `tools/compiler_language_surface_body_parity.py` extends that same bridge only for query/mutation body slots whose identities, occurrence rules, ordering and value modes come directly from the frozen contract; it contains no independent clause inventory. Structured `errors` values enter only when `tools/compiler_typecheck.py` has already produced complete compiler-owned evidence. Stable semantic JSON and SHA-256 hashes deliberately exclude parser locations and source whitespace.

## Implemented normalization

The bridge normalizes these representative legacy surfaces:

- declaration-specific relationship headers into contract-owned named `HeaderArg` facts;
- query/mutation parameter lists into the contract-owned `parameters` HeaderArg when every parameter is losslessly typed;
- unprefixed `entity` fields into the `field` `BodySlot`, including `T?`, list/reference structure and contract-declared field modifiers;
- `opaque` into canonical `alias` identity plus an explicit opacity fact;
- `ref` forms and resolver-backed projections such as `Pet.id` into structured target/projection/resolved-type facts;
- enum cases into first-class body slots;
- `app` profile/version clauses into nested contract body-slot facts;
- `@publicReason(...)` and other contract-declared annotations into target/arity/value-mode checked `ModifierCall` values;
- query `read` and `allow` clauses as expression-valued body slots and query `timeout` as a literal body slot;
- mutation `allow`/`call` as expression-valued body slots and `audit`/`timeout` as literal body slots;
- query/mutation `errors` as ordered `type_ref_list` body slots only from complete compiler-owned standard/resolved error evidence;
- migration versions as literal-valued facts.

Normalization fails closed with stable `AIDL-N###` diagnostics for unsupported or ambiguous frozen facts rather than silently inventing canonical meaning.

## Core reference-projection parity

`tools/compiler_typecheck.py` owns deterministic resolution for legacy `ref` types. Resolution follows one rule: an exact entity resolution wins first. Only when the complete dotted reference resolves to zero entities may the final segment be interpreted as an entity-field projection. Ambiguous exact entity names, ambiguous projection targets, duplicate projected fields and non-parseable projected field types fail closed.

A successful projection produces separate compiler-owned evidence for `target`, `projection` and `projected_type`. Nullable syntax remains an outer `TypeRef(nullable, ...)` concern, so `ref Pet.id?` resolves the same projection as `ref Pet.id` while preserving optionality independently. Legitimate qualified references such as `ref demo.Pet` remain nominal references and are not reinterpreted as `demo`.`Pet` projections.

The production adapter in `tools/compiler_language_surface_integration.py` consumes that Core resolver/typechecker evidence instead of implementing another naming rule. Missing or ambiguous projections produce `AIDL-N012` plus the existing Core `AIDL-T001` where applicable. Qualified nominal references are supplied to the bridge as target-only resolver evidence, preventing the generic bridge's dotted-reference fallback from changing their meaning.

## Operation-signature parity

Contract revision 4 retains the canonical operation-signature fact introduced by revision 2 for `query` and `mutation`: the optional `parameters` HeaderArg with `parameter_list` value mode. Each element has a unique source-order name, a canonical `TypeRef`, and only contract-declared parameter modifiers. No second operation grammar or parallel parameter table is introduced; the existing parser still owns source recognition and the contract-driven bridge remains the construction point.

The current lossless parameter subset uses the compiler's existing Core type facts. Scalars, named/list/reference types already representable by the bridge are normalized, including resolver-backed `ref Pet.id?` where target, projection, projected type and `TypeRef.optional` remain separate. The `default` modifier is admitted for `query.parameter` and `mutation.parameter` because the existing typechecker already validates its expression against the declared parameter type; its canonical form remains a `ModifierCall(argument_mode=expression)`.

Empty parameter lists do not create a semantic fact, so parameterless operations converge regardless of incidental empty-parenthesis source shape. Malformed or untyped parameters, unsupported parameter modifiers, generic operation type parameters and any parameter type that cannot be represented losslessly remain outside the production semantic set. Production admission reports `AIDL-N013`, with bridge evidence such as `AIDL-N015`, rather than hashing a partial approximation.

The same-version formatter can reproduce the supported legacy parameter list from canonical facts. The explicit canonical migration preview still refuses parameterized operation target syntax because the production parser has no separately versioned canonical parameter syntax yet. This preserves formatter/migrator separation.

## Operation-body parity

Contract revision 4 declares these currently executable query/mutation body facts:

- query: `read` and `allow` use `value_mode=expression`; `errors` uses `value_mode=type_ref_list`; `timeout` uses `value_mode=literal` with duration evidence;
- mutation: `allow` and `call` use `value_mode=expression`; `errors` uses `value_mode=type_ref_list`; `audit` and `timeout` use `value_mode=literal`.

`ContractBodyParityBridge` reads slot identity, occurrence, canonical slot ordering and value mode from `spec/language-surface-v1.json`. Scalar text remains derived from the existing parser child text. `errors` is different by design: the bridge receives only the already structured `operation_errors_evidence()` produced by `tools/compiler_typecheck.py`; it never splits or resolves the list itself.

Complete `errors` evidence admits standard errors and nominal members that resolve uniquely to an `error` declaration. Member order is preserved from source while resolved nominal identities canonicalize to compiler-owned targets, so whitespace and equivalent qualified/unqualified spellings do not perturb semantics. Malformed, unresolved, ambiguous and wrong-kind evidence stays incomplete. Production admission then emits `AIDL-N013` and excludes the operation from the complete semantic set rather than hashing a partial approximation.

This admission layer does not alter `_errors`. Existing source-language diagnostic IDs/text and the M10-04 deferral for unresolved nominal error names remain unchanged; the structured evidence is an additional read-only production-admission fact, not a new global resolver or diagnostic rule.

Slots marked `order=canonical` are reordered by contract identity before semantic JSON/hash generation, so equivalent source clause ordering and whitespace converge. Same-version formatting emits normalized legacy clauses, including canonical ordered `errors` members. Canonical migration preview still fails closed for these covered bodies until a separately versioned target syntax is available.

The intentionally richer operation mini-languages remain excluded: `auth`, `cache`, `consistency`, `authorize`, `idempotency` and `transaction` are not flattened into strings or partial body facts. They continue to produce bridge `AIDL-N010` evidence and production `AIDL-N013`, keeping the whole declaration outside the complete production semantic set.

## Lossless query/mutation/app integration

The production normalization envelope is versioned as `aidl.m10.1-production/v5`; the underlying base bridge document envelope remains `aidl.m10.1-normalized/v2`, while contract revision 4 identifies the expanded frozen body surface. The always-integrated lossless set remains `alias`/`opaque`, `entity`, `enum`, `migration`, `client`, `consumer` and `projection`. `query`, `mutation` and `app` are admitted only when the existing parser/compiler facts and frozen contract cover the complete represented shape without approximation.

Current lossless query/mutation/app facts are typed operation parameters, result types, the contract-backed operation body slots above, `app` profile/version slots and contract-declared annotations. Query/mutation/app bodies containing unsupported clauses or incomplete `errors` evidence remain outside the normalized declaration set and emit `AIDL-N013`; they are not hashed as if complete.

Modifier target and arity validation remains owned by `LanguageSurfaceBridge` through `spec/language-surface-v1.json`. Production integration additionally keeps lexical value-mode evidence from the existing parser AST: a contract modifier requiring literal arguments fails with `AIDL-N014` when its source argument is expression-like instead of a literal. No second modifier inventory is introduced.

The compiler-owned `summary` path continues to consume the production semantic hash and diagnostic state in memory. `ProjectSummary.to_json()` deliberately keeps the existing CLI JSON contract unchanged. Canonical IR shape is also unchanged.

## Semantic hash and equivalence

`Declaration.semantic_json()` and `Document.semantic_json()` use deterministic sorted-key compact JSON. Semantic hashes exclude source spans, paths and whitespace. Contract-canonical operation body slots additionally exclude incidental source clause order; `errors` members retain stable source order and canonical compiler-owned nominal identity. Regression coverage proves source-location/whitespace/order independence, representative legacy/canonical operation-signature/body equivalence, stable diagnostics and unchanged Canonical IR semantic hashes for equivalent sources.

## Formatter and migrator split

`LanguageSurfaceBridge.format_legacy()` and the contract body-parity extension remain same-version canonicalization. `migrate_to_canonical_preview()` remains a separate explicit cross-version prototype. Parameterized operations and the covered body slots remain deliberately unsupported by the canonical migration preview until a separately versioned target syntax exists. Neither Core reference resolution nor production normalization invokes language-version migration implicitly.

## Deliberately pending legacy surfaces

The production path still does not losslessly normalize operation generic constraints, structured `auth`/`cache`/`consistency`/`authorize`/`idempotency`/`transaction` clauses, view selections, indexes/invariants, broader app/auth/profile property mini-languages, messaging/topic/queue bodies, workflow/saga/task internals, resource/deployment/sync/UI/test mini-languages, the complete modifier vocabulary, or project-wide expression/type semantics. Parser recovery and token fidelity remain owned by the existing parser.

These surfaces must stay explicit (`AIDL-N010`/`AIDL-N013`/`AIDL-N015` or existing compiler diagnostics) until both frozen-contract representation and compiler-owned evidence are lossless.

## Next sequential M10.1 step

The next dependency-ready package is one remaining structured mini-language—such as auth/cache or idempotency—only if its existing parser/compiler evidence can be represented as explicit frozen facts without flattening or heuristic reconstruction. Broader workflow/messaging/resource/UI/test bodies remain out of scope until their contract representation is equally lossless.

M10.5-03 Kotlin front-end/AST/IR slices remain blocked until the M10.1 compatibility path is complete. This package does not start Kotlin compiler work and does not perform M16.5 syntax adoption.

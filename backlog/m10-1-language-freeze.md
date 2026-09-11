# M10.1 — Normative Language Surface Freeze Gate

Status: **normative language-design authority for the Kotlin front-end migration target**.

This gate is sequenced after completed M10 Core conformance, before M10.5, before M10.5-03 front-end/IR migration, and before any further M16.5 syntax adoption. Migration-neutral M10.5 scaffolding may continue only where the existing M10.5 roadmap permits it; no Kotlin parser/AST/IR slice may encode a language-surface choice absent from `spec/language-surface-v1.json`.

## Authority and compatibility

`docs/m10-1-language-surface-freeze.md` and `spec/language-surface-v1.json` are the normative target design. `docs/06-grammar.md` remains the grammar for the currently accepted legacy source version until a separately versioned parser/migrator change is implemented. M16.5 design/evaluation material is evidence only where it does not conflict with this freeze; M10.1 wins on conflict.

Legacy compatibility is one-way and versioned: **legacy parse -> canonical AST/IR -> canonical formatter/migrator**. Equivalent legacy and canonical representations must converge on the same normalized semantics/hash. A formatter never performs a language-version migration implicitly.

## Frozen semantic decisions

- Canonical declarations follow `[export] <kind> <name?> [(named-args)] [-> type] { slots }`.
- `NamePolicy` is exactly `required | optional | none`.
- `HeaderArgs` are named semantic facts; occurrence of the argument-list form is independent from each argument's own occurrence.
- `BodySlot` owns explicit occurrence, ordering and uniqueness semantics.
- `TypeRef.optional` is the sole meaning of `T?`; collection/body cardinality is separate.
- `ReferenceProjection` represents target, projection and resolved projected type separately. `Pet.id` is not an opaque dotted string.
- `ModifierCall` owns target set, arity and argument value mode. Invalid target, arity or value mode is rejected even when tokens parse.
- Literal and expression positions are distinct contract modes.
- Enum cases are first-class body slots.
- Formatter canonicalization and language-version migration remain separate operations.

## Inventory disposition

All declaration kinds listed by `docs/06-grammar.md` remain semantic declaration kinds in v1. `module` and `import` remain file directives. Current positional relationship headers, unprefixed entity fields, `opaque`, legacy `ref` spellings and heterogeneous modifier tails are compatibility source forms whose semantics normalize into the frozen model; no semantic declaration kind is removed by this package.

## Gates

1. **M10.1 Freeze** — target design, contract instance and regression corpus are authoritative.
2. **M10.5-03** — Kotlin front-end/IR slices may begin only after the M10.1 compatibility path has executable parity for the semantics they encode.
3. **M16.5** — later syntax adoption that changes the frozen model requires an explicit versioned language decision and compatibility plan.
4. **Parser/AST/IR migration** — production integration proceeds only as bounded M10.1 slices with differential evidence; broad replacement remains out of scope until compatibility is complete.

## Compatibility bridge status

`tools/compiler_language_surface.py` consumes `spec/language-surface-v1.json` as the single construction contract and normalizes representative legacy parser nodes into immutable canonical declarations, body slots, type/reference facts and modifier calls. `docs/m10-1-compatibility-bridge.md` records the executable boundary.

`tools/compiler_language_surface_integration.py` consumes real `CompilerAnalysis`/`CompilerProject` facts. The always-lossless production set remains `alias`/`opaque`, `entity`, `enum`, `migration`, `client`, `consumer` and `projection`.

The Core resolver/typechecker now has explicit frozen legacy reference-projection parity:

- exact entity resolution always wins;
- only zero exact entity matches permit interpreting the final dotted segment as a field projection;
- `ref Pet.id` and `ref Pet.id?` resolve target, projection and projected type separately when exactly one entity and exactly one typed field exist;
- nullable wrapping remains independent from projection resolution;
- unresolved/ambiguous targets, duplicate/missing fields and invalid projected field types fail closed;
- legitimate qualified nominal references such as `ref demo.Pet` retain their existing meaning and are not reinterpreted heuristically.

Production normalization now conditionally admits `query`, `mutation` and `app` only where existing compiler/parser facts are lossless under the frozen contract. Current admitted facts are parameterless operation result types, query `read` expression slots, app profile/version slots and contract-declared annotations. Unsupported operation parameters or body clauses emit `AIDL-N013` and remain outside the semantic hash rather than being approximated.

Modifier target/arity remain contract-driven through `LanguageSurfaceBridge`. Literal-vs-expression argument evidence is checked against the existing parser AST; expression-like input in a literal-only modifier position emits `AIDL-N014`.

The production semantic envelope is now `aidl.m10.1-production/v2`. The compiler-owned in-memory summary consumes its hash/diagnostic state, while CLI JSON and Canonical IR schemas remain unchanged.

M10.1 remains open. The next dependency-ready step is the narrow operation-signature/remaining body-modifier parity slice. Parameter facts must not be normalized until the frozen contract has a lossless canonical representation. M10.5-03 remains blocked for semantic front-end/AST/IR work until the relevant compatibility path is complete.

## Required regression set

The executable contract regression covers name policies, body occurrence/order/uniqueness, enum cases, `Pet.id` projection, modifier target/arity, literal-vs-expression separation, app profiles, migration and representative query behavior.

Production integration additionally proves:

- `ref Pet.id` and `ref Pet.id?` Core acceptance with separate target/projection/projected-type evidence;
- preserved `TypeRef.optional` semantics;
- unchanged exact qualified entity-reference behavior;
- fail-closed unresolved/ambiguous projection diagnostics (`AIDL-T001`/`AIDL-N012`);
- lossless parameterless query/mutation/app normalization;
- modifier target, arity and literal value-mode diagnostics (`AIDL-N008`, `AIDL-N009`, `AIDL-N014`);
- explicit exclusion of non-lossless parameterized operations (`AIDL-N013`);
- legacy/canonical semantic-hash equivalence for representative facts;
- deterministic diagnostics and source-location/whitespace-independent M10.1 hashes;
- unchanged Canonical IR semantic hashes for equivalent sources;
- unchanged CLI JSON contract and formatter/migrator separation.

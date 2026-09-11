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
- Query/mutation operation parameters are a contract-owned `parameters` HeaderArg with `parameter_list` value mode. Each parameter owns a unique name, a `TypeRef`, and only contract-declared parameter modifiers; `default` remains an expression-valued `ModifierCall`.
- Query body parity now includes contract-owned `read` and `allow` expression slots plus literal `timeout`; mutation parity includes expression `allow`/`call` plus literal `audit`/`timeout`. These singleton slots normalize in contract canonical order rather than incidental source order.
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

`tools/compiler_language_surface.py` consumes `spec/language-surface-v1.json` as the single construction contract and normalizes representative legacy parser nodes into immutable canonical declarations, header arguments, operation parameters, body slots, type/reference facts and modifier calls. `tools/compiler_language_surface_body_parity.py` extends that bridge only by interpreting scalar query/mutation body slots already declared by the same contract; it owns no separate clause inventory. `docs/m10-1-compatibility-bridge.md` records the executable boundary.

`tools/compiler_language_surface_integration.py` consumes real `CompilerAnalysis`/`CompilerProject` facts. The always-lossless production set remains `alias`/`opaque`, `entity`, `enum`, `migration`, `client`, `consumer` and `projection`; `query`, `mutation` and `app` are admitted only when all represented facts are lossless.

The Core resolver/typechecker has explicit frozen legacy reference-projection parity:

- exact entity resolution always wins;
- only zero exact entity matches permit interpreting the final dotted segment as a field projection;
- `ref Pet.id` and `ref Pet.id?` resolve target, projection and projected type separately when exactly one entity and exactly one typed field exist;
- nullable wrapping remains independent from projection resolution;
- unresolved/ambiguous targets, duplicate/missing fields and invalid projected field types fail closed;
- legitimate qualified nominal references such as `ref demo.Pet` retain their existing meaning and are not reinterpreted heuristically.

Production normalization admits lossless typed query/mutation operation signatures using contract revision 3. Parameter order and names are preserved; parameter types use the same `TypeRef`/resolver evidence as fields and result types; `TypeRef.optional` remains independent; and `default` is represented as an expression-valued `ModifierCall` targeted to `query.parameter` or `mutation.parameter`. Parameterless operations normalize to the same semantic shape whether or not an empty parameter list is present.

Contract revision 3 additionally admits only the scalar operation-body facts for which the existing parser already carries lossless complete text: query `allow`/`timeout` and mutation `allow`/`call`/`audit`/`timeout`, alongside the existing query `read`. Expression slots preserve normalized expression text; `timeout` and `audit` remain literal-valued facts. All contract-canonical singleton slots are ordered by contract identity before hashing, so source clause order and whitespace do not perturb semantics.

Generic operation type parameters, malformed/untyped parameters, unsupported parameter modifiers, and body clauses not fully represented by the frozen contract remain excluded from the complete production semantic set. In particular `auth`, `errors`, `cache`, `consistency`, `authorize`, `idempotency`, `transaction` and their nested mini-languages remain pending. They produce stable fail-closed diagnostics (`AIDL-N013` with bridge evidence such as `AIDL-N010`/`AIDL-N015`) instead of heuristic canonical facts.

Modifier target/arity remain contract-driven through `LanguageSurfaceBridge`. Literal-vs-expression annotation evidence is checked against the existing parser AST; expression-like input in a literal-only modifier position emits `AIDL-N014`.

The bridge semantic envelope remains `aidl.m10.1-normalized/v2` for the base bridge; production body parity is explicitly versioned by contract revision 3 and production envelope `aidl.m10.1-production/v4`. The compiler-owned in-memory summary consumes the production hash/diagnostic state, while CLI JSON and Canonical IR schemas remain unchanged.

M10.1 remains open. The next dependency-ready step is structured parity for one remaining mini-language whose parser/compiler evidence can be represented without flattening—for example auth/errors/cache or idempotency—before considering broader workflow/messaging/resource/UI/test bodies. M10.5-03 remains blocked for semantic front-end/AST/IR work until the relevant compatibility path is complete.

## Required regression set

The executable contract regression covers name policies, body occurrence/order/uniqueness, enum cases, `Pet.id` projection, modifier target/arity, literal-vs-expression separation, app profiles, migration and representative query behavior.

Production integration additionally proves:

- `ref Pet.id` and `ref Pet.id?` Core acceptance with separate target/projection/projected-type evidence;
- preserved `TypeRef.optional` semantics and exact qualified entity-reference priority;
- fail-closed unresolved/ambiguous projection diagnostics (`AIDL-T001`/`AIDL-N012`);
- lossless typed query/mutation parameters, including projection-backed parameter types and expression-valued defaults;
- contract-backed query `read`/`allow`/`timeout` and mutation `allow`/`call`/`audit`/`timeout` body parity;
- semantic equivalence between legacy operation signatures/body facts and independently constructed canonical facts;
- deterministic body/parameter diagnostics and source-location/whitespace/source-clause-order-independent M10.1 hashes;
- explicit exclusion of generic, malformed, unsupported-modifier and unsupported mini-language operation shapes (`AIDL-N013`);
- modifier target, arity and literal value-mode diagnostics (`AIDL-N008`, `AIDL-N009`, `AIDL-N014`);
- unchanged Canonical IR semantic hashes for equivalent sources;
- unchanged CLI JSON contract and formatter/migrator separation.

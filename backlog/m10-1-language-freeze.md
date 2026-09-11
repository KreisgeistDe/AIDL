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
- Query body parity includes contract-owned `read` and `allow` expression slots, ordered `errors` type-ref lists, plus literal `timeout`; mutation parity includes expression `allow`/`call`, ordered `errors` type-ref lists, plus literal `audit`/`timeout`. Singleton slots normalize in contract canonical order rather than incidental source order while members of `errors` preserve source order.
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

## Stable work packages

M10.1 roadmap identity is package-based, not PR-based. Merged PRs and tests are evidence assigned to these stable packages; they do not create new roadmap IDs. A checked package means the current repository still contains the required normative decision, implementation and regression evidence.

- [x] **M10.1-01 — Freeze the canonical language-surface contract.** The normative freeze, machine-readable contract and contract regressions are integrated. Evidence includes the accepted freeze package originally merged through PR #59.
- [x] **M10.1-02 — Establish the executable legacy-to-canonical compatibility bridge.** The contract-driven bridge, deterministic normalized semantics/hashes and explicit formatter/migrator separation are integrated. Evidence includes PR #60.
- [x] **M10.1-03 — Integrate canonical normalization into the production compiler path.** Real `CompilerAnalysis`/`CompilerProject` facts feed bounded production normalization with deterministic fail-closed exclusion outside the lossless envelope. Evidence includes PRs #61 and #62.
- [x] **M10.1-04 — Close operation signatures and baseline body parity.** Typed query/mutation signatures, reference projections, defaults and contract-backed scalar body slots are integrated. Evidence includes PRs #63 and #64.
- [x] **M10.1-05 — Close structured operation error parity.** Compiler-owned structured `errors` evidence and contract revision 4 production admission are integrated with ordered deterministic semantics and fail-closed incomplete evidence. Evidence includes PRs #65 and #66.
- [ ] **M10.1-06 — Close structured operation policy semantics.** Complete `auth`, `authorize`, `cache` and `consistency` semantics through frozen-contract facts plus compiler-owned evidence. PR #67 provides the compiler-owned auth evidence prerequisite. PR #68 adds the bounded `policy-bool-no-parameters/v1` qualifiedName auth-target contract: a unique non-generic, parameterless `policy` returning `bool` is eligible, while unresolved, ambiguous, wrong-kind, generic, parameterized and non-`bool` targets remain fail-closed. These merged prerequisites do **not** establish auth Production-Parity, and this package remains open.
- [ ] **M10.1-07 — Close operation execution semantics.** Complete `idempotency`, `transaction`, remaining operation modifiers and any frozen-v1 operation generics/constraints that require an explicit compatibility disposition. Unsupported shapes remain fail-closed until represented losslessly.
- [ ] **M10.1-08 — Close declaration-family production parity.** Every remaining frozen-v1 declaration family must have an explicit disposition: `production-parity`, `intentionally excluded`, or `not applicable`, backed by deterministic evidence rather than inferred from parser acceptance.
- [ ] **M10.1-09 — Add complete language-surface coverage and differential conformance.** Maintain a complete machine-readable frozen-v1 inventory/disposition, differential legacy/canonical evidence, and CI drift protection covering compatibility and Production Normalization.
- [ ] **M10.1-10 — Certify M10.1 closure and unblock M10.5-03.** Audit all package evidence, close the regression matrix and Production Semantic Envelope, and unblock M10.5-03 only when it can implement the frozen surface without making any unresolved language decision of its own.

## M10.1 acceptance criteria

M10.1 closes only when all of the following hold:

- Every frozen-v1 semantic fact is normalized losslessly or rejected deterministically fail-closed; no heuristic partial semantics are admitted as complete.
- Equivalent legacy and canonical representations converge on identical semantic facts and stable semantic hashes.
- Production Normalization is derived only from `spec/language-surface-v1.json` plus compiler-owned evidence; there is no parallel grammar, independent declaration/body inventory, or parallel semantic table.
- Same-version formatting and explicit language-version migration remain separate operations.
- Query/mutation and every required frozen-v1 declaration family have complete production parity or an explicit justified exclusion/not-applicable disposition.
- The complete coverage/compatibility inventory and differential conformance checks are deterministic and protected against drift in CI.
- M10.5-03 can implement the frozen front-end/IR model without inventing, selecting or resolving a language decision not already closed by M10.1.

## Compatibility bridge status

`tools/compiler_language_surface.py` consumes `spec/language-surface-v1.json` as the single construction contract and normalizes representative legacy parser nodes into immutable canonical declarations, header arguments, operation parameters, body slots, type/reference facts and modifier calls. `tools/compiler_language_surface_body_parity.py` extends that bridge only by interpreting operation body slots already declared by the same contract; it owns no separate clause inventory. Structured query/mutation `errors` admission is supplied only by `tools/compiler_typecheck.py` through compiler-owned ordered resolution evidence. `docs/m10-1-compatibility-bridge.md` records the executable boundary.

`tools/compiler_language_surface_integration.py` consumes real `CompilerAnalysis`/`CompilerProject` facts. The always-lossless production set remains `alias`/`opaque`, `entity`, `enum`, `migration`, `client`, `consumer` and `projection`; `query`, `mutation` and `app` are admitted only when all represented facts are lossless.

The Core resolver/typechecker has explicit frozen legacy reference-projection parity:

- exact entity resolution always wins;
- only zero exact entity matches permit interpreting the final dotted segment as a field projection;
- `ref Pet.id` and `ref Pet.id?` resolve target, projection and projected type separately when exactly one entity and exactly one typed field exist;
- nullable wrapping remains independent from projection resolution;
- unresolved/ambiguous targets, duplicate/missing fields and invalid projected field types fail closed;
- legitimate qualified nominal references such as `ref demo.Pet` retain their existing meaning and are not reinterpreted heuristically.

Production normalization admits lossless typed query/mutation operation signatures using contract revision 4. Parameter order and names are preserved; parameter types use the same `TypeRef`/resolver evidence as fields and result types; `TypeRef.optional` remains independent; and `default` is represented as an expression-valued `ModifierCall` targeted to `query.parameter` or `mutation.parameter`. Parameterless operations normalize to the same semantic shape whether or not an empty parameter list is present.

Contract revision 4 retains scalar operation-body parity and additionally admits `errors` only when compiler-owned structured evidence is complete. Query `read`/`allow` and mutation `allow`/`call` remain expression-valued; `timeout` and `audit` remain literal-valued. `errors` uses contract-owned `type_ref_list` facts: standard errors and nominal members uniquely resolved to `error` declarations normalize in stable source-member order. Malformed, unresolved, ambiguous and wrong-kind members fail closed and keep the whole operation outside the complete production semantic set. Contract-canonical singleton slots are ordered by contract identity before hashing, so source clause order and whitespace do not perturb semantics.

Generic operation type parameters, malformed/untyped parameters, unsupported parameter modifiers, and body clauses not fully represented by the frozen contract remain excluded from the complete production semantic set. In particular `auth`, `cache`, `consistency`, `authorize`, `idempotency`, `transaction` and their nested mini-languages remain pending. They produce stable fail-closed diagnostics (`AIDL-N013` with bridge evidence such as `AIDL-N010`/`AIDL-N015`) instead of heuristic canonical facts. Incomplete `errors` evidence likewise yields fail-closed production admission without changing the compiler's existing `_errors` diagnostics or the M10-04 unresolved-nominal deferral.

The merged auth prerequisites provide diagnostic-neutral compiler-owned evidence without changing that production envelope. Builtin `public`, `authenticated` and `service` modes are explicit and complete at the evidence layer. Qualified auth names use the bounded `policy-bool-no-parameters/v1` target contract from PR #68: exactly one non-generic, parameterless `policy` with declared result `bool` is eligible and complete evidence, while unresolved, ambiguous, wrong-kind, generic, parameterized and non-`bool` targets remain explicit fail-closed states. This evidence and target contract still do not add an `auth` body slot to the frozen contract and therefore do not establish auth Production-Parity.

Modifier target/arity remain contract-driven through `LanguageSurfaceBridge`. Literal-vs-expression annotation evidence is checked against the existing parser AST; expression-like input in a literal-only modifier position emits `AIDL-N014`.

The bridge semantic envelope remains `aidl.m10.1-normalized/v2` for the base bridge; production errors parity is explicitly versioned by contract revision 4 and production envelope `aidl.m10.1-production/v5`. The compiler-owned in-memory summary consumes the production hash/diagnostic state, while CLI JSON and Canonical IR schemas remain unchanged.

M10.1 remains open at **M10.1-06**. The next auth step is a bounded contract-owned Production-Parity slice that represents eligible builtins and qualified-policy evidence losslessly while keeping unsupported auth states excluded; the package remains incomplete until `auth`, `authorize`, `cache` and `consistency` have explicit frozen-contract/compiler-evidence dispositions and Production-Parity where required. M10.5-03 remains blocked for semantic front-end/AST/IR work until all relevant M10.1 packages through closure certification are complete.

## Required regression set

The executable contract regression covers name policies, body occurrence/order/uniqueness, enum cases, `Pet.id` projection, modifier target/arity, literal-vs-expression separation, app profiles, migration and representative query behavior.

Production integration additionally proves:

- `ref Pet.id` and `ref Pet.id?` Core acceptance with separate target/projection/projected-type evidence;
- preserved `TypeRef.optional` semantics and exact qualified entity-reference priority;
- fail-closed unresolved/ambiguous projection diagnostics (`AIDL-T001`/`AIDL-N012`);
- lossless typed query/mutation parameters, including projection-backed parameter types and expression-valued defaults;
- contract-backed query `read`/`allow`/`errors`/`timeout` and mutation `allow`/`errors`/`call`/`audit`/`timeout` body parity;
- ordered standard/resolved `errors` normalization, including qualified nominal errors, with malformed/unresolved/ambiguous/wrong-kind evidence excluded from complete semantics;
- semantic equivalence between legacy operation signatures/body facts and independently constructed canonical facts;
- deterministic body/parameter diagnostics and source-location/whitespace/source-clause-order-independent M10.1 hashes;
- explicit exclusion of generic, malformed, unsupported-modifier and unsupported mini-language operation shapes (`AIDL-N013`);
- modifier target, arity and literal value-mode diagnostics (`AIDL-N008`, `AIDL-N009`, `AIDL-N014`);
- unchanged existing `_errors` diagnostic IDs/text and unresolved-nominal M10-04 deferral;
- unchanged Canonical IR semantic hashes for equivalent sources;
- unchanged CLI JSON contract and formatter/migrator separation.

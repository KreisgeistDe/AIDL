# M10.1 — Normative Language Surface Freeze Gate

Status: **normative language-design authority for the Kotlin front-end migration target; closure certified for frozen-v1 revision 4**.

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

1. **M10.1 Freeze** — target design, contract instance and regression corpus are authoritative and closure-certified for revision 4.
2. **M10.5-03** — Kotlin front-end/IR slices are unblocked only to implement the certified frozen-v1 revision 4 model through the existing Python-versus-Kotlin differential gates; this does not authorize a semantic change.
3. **M16.5** — later syntax adoption that changes the frozen model requires an explicit versioned language decision and compatibility plan.
4. **Parser/AST/IR migration** — production migration must remain bounded and differential; M10.1 certification is an input contract, not permission for a broad replacement or silent semantic divergence.

## Stable work packages

M10.1 roadmap identity is package-based, not PR-based. Merged PRs and tests are evidence assigned to these stable packages; they do not create new roadmap IDs. A checked package means the current repository still contains the required normative decision, implementation and regression evidence.

- [x] **M10.1-01 — Freeze the canonical language-surface contract.** The normative freeze, machine-readable contract and contract regressions are integrated. Evidence includes the accepted freeze package originally merged through PR #59.
- [x] **M10.1-02 — Establish the executable legacy-to-canonical compatibility bridge.** The contract-driven bridge, deterministic normalized semantics/hashes and explicit formatter/migrator separation are integrated. Evidence includes PR #60.
- [x] **M10.1-03 — Integrate canonical normalization into the production compiler path.** Real `CompilerAnalysis`/`CompilerProject` facts feed bounded production normalization with deterministic fail-closed exclusion outside the lossless envelope. Evidence includes PRs #61 and #62.
- [x] **M10.1-04 — Close operation signatures and baseline body parity.** Typed query/mutation signatures, reference projections, defaults and contract-backed scalar body slots are integrated. Evidence includes PRs #63 and #64.
- [x] **M10.1-05 — Close structured operation error parity.** Compiler-owned structured `errors` evidence and contract revision 4 production admission are integrated with ordered deterministic semantics and fail-closed incomplete evidence. Evidence includes PRs #65 and #66.
- [x] **M10.1-06 — Close structured operation policy semantics.** The frozen-v1 `allow` BodySlot is the contract-owned authorize surface and has Production-Parity for query/mutation. Contract revision 4 deliberately has no `auth`, `cache` or `consistency` BodySlots, so those legacy source concepts have explicit `excluded` dispositions and continue to fail closed rather than inventing canonical facts. PR #67 remains compiler-owned auth evidence and PR #68 remains the bounded `policy-bool-no-parameters/v1` auth-target prerequisite; neither broadens the frozen contract. `tools/compiler_operation_policy_parity.py` derives these dispositions directly from the contract and executable regressions protect the boundary.
- [x] **M10.1-07 — Close operation execution semantics.** `TypeRef.range` and operation-parameter `default` are the frozen-v1 execution facts with Production-Parity for query/mutation. Generic TypeRef arguments, non-range constraints and operation generics are explicit fail-closed exclusions; mutation `idempotency` and `transaction` are likewise excluded because revision 4 declares no such BodySlots. `tools/compiler_operation_execution_parity.py` derives the package audit from the frozen contract and existing bridges; no new parser, runtime or canonical execution fact is introduced.
- [x] **M10.1-08 — Close declaration-family production parity.** `tools/compiler_declaration_family_parity.py` derives all 48 canonical semantic declaration kinds directly from frozen-v1 and projects admission from the existing Production Normalization gates. `alias`, `entity`, `enum`, `migration`, `client`, `consumer`, `projection`, `app`, `query` and `mutation` are the ten admitted canonical kinds; the other 38 frozen kinds have explicit intentional non-admission/fail-closed dispositions. `module`/`import` remain file directives and legacy `opaque` maps to canonical `alias`, so neither adds a canonical declaration kind.
- [x] **M10.1-09 — Add complete language-surface coverage and differential conformance.** `tools/compiler_language_surface_coverage.py` walks every non-example frozen-v1 contract leaf generically and correlates it with the existing declaration-family, policy, execution and Production Normalization evidence. Modifier target/arity/value mode, HeaderArg/BodySlot occurrence/order/uniqueness, TypeRef optional/range facts and reference-projection shapes remain derived from the frozen contract and executable bridges rather than a second semantic table. `tools/test_m10_1_language_surface_coverage.py` adds byte-stable coverage output, compiler/contract drift detection, independent canonical-fact differential checks and production fail-closed regressions.
- [x] **M10.1-10 — Certify M10.1 closure and unblock M10.5-03.** `tools/compiler_language_surface_certification.py` composes the integrated contract-derived audits, verifies the complete Production Semantic Envelope and acceptance matrix, fails closed on unresolved disposition/drift, and records no unresolved language decision for M10.5-03. `docs/m10-1-closure-certification.md` defines the bounded unblock: differential implementation of frozen-v1 revision 4 only, with any semantic change requiring a separately versioned language decision.

## M10.1 acceptance criteria

M10.1 closes only when all of the following hold; `aidl.m10.1-closure-certification/v1` now certifies each condition from executable repository evidence:

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

M10.1-06 makes the policy disposition explicit without changing contract revision 4. The roadmap concept `authorize` maps to frozen-v1's query/mutation `allow` expression BodySlot and therefore already has contract-owned Production-Parity through `ContractBodyParityBridge`. The legacy `auth`, `cache` and `consistency` concepts are absent from the query/mutation BodySlot inventory; they are explicitly `excluded` from frozen-v1 Production Normalization and remain on the existing `AIDL-N010` -> `AIDL-N013` fail-closed path. An `authorize` source keyword is likewise not a separate frozen-v1 surface: source syntax continues to use `allow`, so no alias or parser expansion is introduced. `tools/compiler_operation_policy_parity.py` derives this audit from `spec/language-surface-v1.json` instead of maintaining an independent clause inventory.

The merged auth prerequisites remain diagnostic-neutral compiler-owned evidence outside the canonical BodySlot envelope. Builtin `public`, `authenticated` and `service` modes are explicit and complete at the evidence layer. Qualified auth names use the bounded `policy-bool-no-parameters/v1` target contract from PR #68: exactly one non-generic, parameterless `policy` with declared result `bool` is eligible and complete evidence, while unresolved, ambiguous, wrong-kind, generic, parameterized and non-`bool` targets remain explicit fail-closed states. Because frozen-v1 declares no operation `auth` BodySlot, that evidence cannot be promoted into canonical operation semantics without a separately versioned language decision; M10.1-06 therefore closes by explicit exclusion, not by treating PR #67/#68 as Production-Parity.

M10.1-07 closes the remaining operation-execution compatibility dispositions without changing frozen-v1 revision 4. `TypeRef.range` is contract-owned structured min/max evidence and is preserved recursively by `CompilerLanguageSurfaceBridge`; operation parameter `default` is a contract-declared expression-valued `ModifierCall` for both query and mutation. Generic TypeRef arguments and non-range constraint shapes remain on the existing `AIDL-N015` -> `AIDL-N013` fail-closed path, while operation generic type parameters remain outside the frozen operation header facts and are rejected by the production losslessness gate. Mutation `idempotency` and `transaction` are absent from the contract BodySlot inventory, so legacy source clauses continue to produce `AIDL-N010` bridge evidence and are excluded through `AIDL-N013` instead of inventing canonical execution semantics. `tools/compiler_operation_execution_parity.py` derives these dispositions directly from `LanguageSurfaceBridge` and `ContractBodyParityBridge` and emits deterministic `aidl.m10.1-operation-execution-parity/v1` audit JSON.

M10.1-08 closes declaration-family disposition evidence without changing the frozen contract or production compiler semantics. `tools/compiler_declaration_family_parity.py` reads the canonical declaration-kind inventory from `LanguageSurfaceBridge().contract` and reads current admission from the existing `_ALWAYS_INTEGRATED` and `_LOSSLESS_CANDIDATES` Production Normalization gates. Legacy `opaque` is canonicalized to `alias` only for the audit projection. Families absent from those compiler-owned admission gates remain explicitly `intentionally_excluded`/`non_admitted`; parser acceptance or base bridge normalization alone is not promoted to complete production semantics. The deterministic `aidl.m10.1-declaration-family-parity/v1` audit reports 48 canonical kinds, ten production-parity admissions and 38 intentional non-admissions.

M10.1-09 closes complete coverage/differential evidence without changing the frozen contract or parser/runtime/IR semantics. `tools/compiler_language_surface_coverage.py` derives every normative/compatibility leaf except illustrative examples from the exact frozen contract, then attaches production admission from the existing declaration-family audit and target-dependent modifier dispositions from the same compiler gates. TypeRef optional/range and reference-projection shapes are sampled from the executable compatibility bridge itself, while existing policy/execution audits carry their established exclusions. The builder compares the base and body bridges against the same contract and rejects drift before emitting deterministic `aidl.m10.1-language-surface-coverage/v1` JSON. Focused unittest differentials compare representative legacy entity/operation sources with independently constructed canonical `Declaration` facts, compare equivalent production sources for byte-identical semantic JSON/hash, and retain `AIDL-N013` fail-closed evidence for generic/non-range/idempotency shapes.

M10.1-10 certifies those integrated facts without adding language semantics. `tools/compiler_language_surface_certification.py` requires the frozen M10.1 authority/status and common contract revision, complete unique coverage leaves, explicit declaration/policy/execution dispositions, fail-closed boundaries for every exclusion, executable TypeRef/reference-projection shapes, distinct deterministic formatter/migration operations and all ten roadmap packages complete. The deterministic `aidl.m10.1-closure-certification/v1` result records the certified Production Semantic Envelope, an empty unresolved-language-decision set and the bounded M10.5-03 unblock condition.

Modifier target/arity remain contract-driven through `LanguageSurfaceBridge`. Literal-vs-expression annotation evidence is checked against the existing parser AST; expression-like input in a literal-only modifier position emits `AIDL-N014`.

The bridge semantic envelope remains `aidl.m10.1-normalized/v2` for the base bridge and `aidl.m10.1-production/v5` for production normalization. Policy, execution, declaration-family, complete-coverage and closure evidence add only deterministic audit envelopes `aidl.m10.1-operation-policy-parity/v1`, `aidl.m10.1-operation-execution-parity/v1`, `aidl.m10.1-declaration-family-parity/v1`, `aidl.m10.1-language-surface-coverage/v1` and `aidl.m10.1-closure-certification/v1`; they do not alter canonical hashes, parser behavior, CLI JSON, runtime behavior or Canonical IR schemas.

M10.1 is complete. The closure certification proves no unresolved revision-4 language decision remains for M10.5-03. M10.5-03 is therefore unblocked only for bounded differential implementation of the frozen front-end/IR model; Python remains the reference/conformance implementation under the M10.5 roadmap, and any semantic change still requires a separately versioned language decision.

## Required regression set

The executable contract regression covers name policies, body occurrence/order/uniqueness, enum cases, `Pet.id` projection, modifier target/arity, literal-vs-expression separation, app profiles, migration and representative query behavior.

Production integration additionally proves:

- `ref Pet.id` and `ref Pet.id?` Core acceptance with separate target/projection/projected-type evidence;
- preserved `TypeRef.optional` semantics and exact qualified entity-reference priority;
- fail-closed unresolved/ambiguous projection diagnostics (`AIDL-T001`/`AIDL-N012`);
- lossless typed query/mutation parameters, including projection-backed parameter types and expression-valued defaults;
- contract-backed query `read`/`allow`/`errors`/`timeout` and mutation `allow`/`errors`/`call`/`audit`/`timeout` body parity;
- ordered standard/resolved `errors` normalization, including qualified nominal errors, with malformed/unresolved/ambiguous/wrong-kind evidence excluded from complete semantics;
- contract-derived M10.1-06 policy dispositions for both query and mutation, byte-stable audit JSON, lossless `allow` normalization, and fail-closed `auth`/`cache`/`consistency` source clauses;
- contract-derived M10.1-07 execution dispositions for query/mutation, byte-stable audit JSON, lossless `TypeRef.range` and `default` preservation, and fail-closed generic/non-range/`idempotency`/`transaction` boundaries;
- contract-derived M10.1-08 declaration-family dispositions with exact frozen inventory parity, production admission projected from existing compiler gates, explicit non-admission for every other frozen kind, byte-stable audit JSON and drift derivation without a parallel declaration table;
- contract-derived M10.1-09 complete contract-leaf coverage, modifier-target production correlation, executable TypeRef/reference-projection shapes, byte-stable coverage JSON and bridge/contract drift rejection;
- M10.1-10 closure certification with a complete seven-condition acceptance matrix, explicit Production Semantic Envelope, empty unresolved-language-decision set, deterministic JSON and bounded M10.5-03 unblock signal;
- semantic equivalence between legacy operation/entity facts and independently constructed canonical facts;
- deterministic body/parameter diagnostics and source-location/whitespace/source-clause-order-independent M10.1 hashes;
- explicit exclusion of generic, malformed, unsupported-modifier and unsupported mini-language operation shapes (`AIDL-N013`);
- modifier target, arity and literal value-mode diagnostics (`AIDL-N008`, `AIDL-N009`, `AIDL-N014`);
- unchanged existing `_errors` diagnostic IDs/text and unresolved-nominal M10-04 deferral;
- unchanged Canonical IR semantic hashes for equivalent sources;
- unchanged CLI JSON contract and formatter/migrator separation.

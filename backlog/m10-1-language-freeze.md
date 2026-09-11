# M10.1 — Normative Language Surface Freeze Gate

Status: **normative language-design authority for the Kotlin front-end migration target**.

This gate is sequenced after completed M10 Core conformance, before M10.5, before M10.5-03 front-end/IR migration, and before any further M16.5 syntax adoption. Migration-neutral M10.5 scaffolding (module boundaries, build wiring, serialization/test infrastructure and differential-harness plumbing) may continue only where the existing M10.5 roadmap permits it, but no Kotlin parser/AST/IR slice may encode a language-surface choice that is not represented by the frozen contract in `spec/language-surface-v1.json`.

## Authority and compatibility

For the next compiler front-end, `docs/m10-1-language-surface-freeze.md` and `spec/language-surface-v1.json` are the normative target design. `docs/06-grammar.md` remains the normative grammar for the currently accepted legacy source version until a separately versioned parser/migrator change is implemented. M16.5 design/evaluation documents remain evidence and tooling/adoption gates; where an M16.5 candidate conflicts with this freeze, M10.1 wins. There is no permanent parallel grammar.

Legacy compatibility is one-way and versioned: **legacy parse -> canonical AST/IR -> canonical formatter/migrator**. Equivalent legacy and canonical source must converge on the same normalized semantic IR/hash. A formatter never performs a language-version migration implicitly.

## Frozen semantic decisions

- Canonical declarations have the structural direction `[export] <kind> <name?> [(named-args)] [-> type] { slots }`.
- `NamePolicy` is exactly `required | optional | none` and is declaration metadata, never inferred from parser position.
- `HeaderArgs` are named semantic facts. `args?` means the argument-list form itself occurs `0..1`; it does not make every argument optional.
- `BodySlot` owns explicit `occurrence.min/max`, order semantics and uniqueness. `A*` means slot occurrence `0..*`; `R?` means slot occurrence `0..1`. Neither notation changes the referenced/value type.
- `TypeRef.optional` is the sole meaning of `T?`: type optionality. Collection/cardinality is represented separately.
- `TypeRef` includes resolved `ReferenceProjection`; `Pet.id` is represented as target `Pet`, projection `id`, and the resolved projected type, not as an opaque dotted string.
- `ModifierCall` has an explicit target set and argument arity (`min/max`), with argument value modes. A modifier is invalid when target or arity does not match even if its tokens parse.
- Literal and expression positions are distinct contract modes. Literal positions accept only literal values of the declared literal kind; expression positions enter the expression/type checker and may contain references/operators/calls.
- Range/cardinality facts always carry explicit `min` and `max` (`null` means unbounded); punctuation such as `?` or `*` is only surface notation.
- Block-bodied declarations and nested body slots use one ordered slot-container model. Context-specific slot schemas preserve semantic distinctions.
- Enum cases are first-class body slots with required case name and optional explicit wire literal; they are not generic expressions.
- Annotations such as `@publicReason(...)` are structured modifier calls applied to a declared target; their payload follows the modifier's value-mode/arity contract.

## Inventory disposition

Every declaration kind currently listed by `docs/06-grammar.md` remains a canonical semantic `DeclarationKind` in v1: `app`, `auth`, `a11y`, `privacy`, `enum`, `alias`, `value`, `union`, `error`, `entity`, `view`, `api`, `policy`, `query`, `mutation`, `event`, `topic`, `queue`, `consumer`, `projection`, `workflow`, `saga`, `task`, `schedule`, `system`, `service`, `client`, `tenant`, `channel`, `resource`, `media`, `rendition`, `sync`, `migration`, `deployment`, `frontend`, `theme`, `component`, `page`, `form`, `action`, `syncStatus`, `seo`, `nativeFunction`, `nativeComponent`, `fixture`, `test`, `scenario`.

`module` and `import` remain canonical file directives, not declarations. Current declaration-specific positional header spellings (`projection ... from ... into ...`, `client ... for ...`, `migration ... from ... to ...`, `consumer ... on ... from ...`, operation signatures, and equivalent fixed-word-order headers) are **legacy** source forms whose facts normalize into named `HeaderArgs`/result type. Unprefixed entity fields and heterogeneous leaf/block spellings are **legacy** source forms whose facts normalize into typed `BodySlot`s. The `opaque` alias keyword is a **legacy alias spelling** represented canonically by `alias` plus an explicit opacity fact. `ref Qualified.Name` is a **legacy type spelling** represented canonically by `TypeRef(kind=reference, target, projection?)`.

No semantic declaration kind is removed by this package. The items marked **remove from canonical surface** are only redundant source-shape mechanisms: declaration-specific relationship keywords in headers, implicit body-slot identity based solely on parser context, overloading `?/*` to mean both type and metamodel cardinality, opaque dotted reference-projection strings, and untyped modifier tails. Their semantics are retained in named canonical facts.

## Gates

1. **M10.1 Freeze** — this document, target schema, contract instance and regression fixtures are reviewed; no unresolved semantic question remains in the frozen model.
2. **M10.5-03** — Kotlin front-end slices may begin only against the frozen model plus legacy compatibility corpus. Differential parity must compare normalized semantics, not accidental legacy parser node shape.
3. **M16.5** — evaluation/tooling may measure or prototype the frozen target, but later adoption that changes this model requires an explicit versioned language decision and compatibility plan.
4. **Parser/AST/IR migration** — production integration proceeds as bounded M10.1 slices with differential evidence before M10.5-03; broad replacement remains out of scope until the compatibility path is complete.

## Compatibility bridge status

The representative bridge is implemented in `tools/compiler_language_surface.py` and specified operationally in `docs/m10-1-compatibility-bridge.md`. It consumes `spec/language-surface-v1.json` directly, normalizes representative current-parser legacy forms into immutable canonical semantic records, provides deterministic semantic JSON/SHA-256 fingerprints, and separates same-version legacy formatting from explicit target-version migration previews.

Covered executable cases include declaration-specific relationship headers, entity fields, optional/reference types, resolver-backed `Pet.id`, opaque aliases, enum cases, app profile/version slots, `@publicReason`, query `read` expressions, body occurrence/uniqueness checks and modifier target/arity checks. Unsupported body mini-languages are diagnosed instead of silently canonicalized, and migration preview refuses facts that the frozen contract cannot yet express losslessly.

The first bounded production integration is implemented in `tools/compiler_language_surface_integration.py`. It consumes real `CompilerAnalysis`/`CompilerProject` nodes, reuses the existing Core type parser and compiler symbol/import resolution for type/reference evidence, and normalizes only the already-lossless `alias`/`opaque`, `entity`, `enum`, `migration`, `client`, `consumer` and `projection` subset. The compiler-owned `summary` projection consumes the resulting versioned semantic hash and surfaces its integrated declaration count and diagnostic state. Canonical IR shape and production parser acceptance remain unchanged.

`Pet.id?` now has production evidence only when the compiler resolves one `Pet` entity and an actual typechecker-parsable `id` field. Missing or ambiguous projections remain fail-closed with `AIDL-N012`. The legacy `ref Pet.id` spelling deliberately remains non-OK while the current Core typechecker still treats the dotted `ref` as a nominal entity reference; the production adapter does not suppress that existing `AIDL-T001` parity signal.

M10.1 remains open after this production slice. The next dependency-ready step is the narrow Core typechecker/resolver parity package for frozen legacy reference projections plus contract-backed modifier/value-mode evidence, followed by carefully widening production normalization to query/mutation/app surfaces only where existing compiler facts are lossless. M10.5-03 remains blocked until that compatibility path and parity evidence are complete.

## Required regression set

The executable contract regression covers: a `User` entity; `migration`; `@publicReason` on `query getPet`; an `app` profile; all three `NamePolicy` values; BodySlot cardinality/order/uniqueness; modifier target/arity; enum cases; resolved `Pet.id` reference projection; and literal-vs-expression rejection. Negative cases must fail for missing required names, forbidden names, duplicate unique slots, occurrence overflow, wrong modifier target/arity, unresolved projection shape, and expressions supplied to literal-only positions.

Production integration additionally proves: real project/typechecker evidence for `Pet.id?`; stable fail-closed diagnostics for unresolved and legacy `ref` projection cases; source-location/whitespace-independent M10.1 and Canonical IR semantic hashes; deterministic compiler-summary consumption of the M10.1 hash; and semantic equivalence between representative legacy normalization and independently constructed canonical facts.

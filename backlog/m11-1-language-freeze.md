# M11-1 — Normative Language Surface Freeze Gate

Status: **normative language-design authority for the Kotlin front-end migration target**.

This gate is sequenced before M10.5-03 front-end/IR migration and before any further M16.5 syntax adoption. Migrationsneutral M10.5 scaffolding (module boundaries, build wiring, serialization/test infrastructure and differential-harness plumbing) may continue, but no Kotlin parser/AST/IR slice may encode a language-surface choice that is not represented by the frozen contract in `spec/language-surface-v1.json`.

## Authority and compatibility

For the next compiler front-end, `docs/m11-1-language-surface-freeze.md` and `spec/language-surface-v1.json` are the normative target design. `docs/06-grammar.md` remains the normative grammar for the currently accepted legacy source version until a separately versioned parser/migrator change is implemented. M16.5 design/evaluation documents remain evidence and tooling/adoption gates; where an M16.5 candidate conflicts with this freeze, M11-1 wins. There is no permanent parallel grammar.

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

1. **M11-1 Freeze** — this document, target schema, contract instance and regression fixtures are reviewed; no unresolved semantic TODO remains in the frozen model.
2. **M10.5-03** — Kotlin front-end slices may begin only against the frozen model plus legacy compatibility corpus. Differential parity must compare normalized semantics, not accidental legacy parser node shape.
3. **M16.5** — evaluation/tooling may measure or prototype the frozen target, but later adoption that changes this model requires an explicit versioned language decision and compatibility plan.
4. **Parser/AST/IR migration** — broad production implementation is the next sequential M11-1 package, not part of this freeze commit.

## Required regression set

The executable contract regression covers: a `User` entity; `migration`; `@publicReason` on `query getPet`; an `app` profile; all three `NamePolicy` values; BodySlot cardinality/order/uniqueness; modifier target/arity; enum cases; resolved `Pet.id` reference projection; and literal-vs-expression rejection. Negative cases must fail for missing required names, forbidden names, duplicate unique slots, occurrence overflow, wrong modifier target/arity, unresolved projection shape, and expressions supplied to literal-only positions.

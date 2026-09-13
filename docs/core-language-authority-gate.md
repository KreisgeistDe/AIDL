# Core Language Authority Gate

## Status

Phase I1 is integrated on `main`. Phase I2 is the current implementation candidate. It adds Core-owned semantic contracts and an ordinary AIDL `core.domain` module while preserving the minimal Bootstrap Kernel boundary. It still does **not** complete the project-wide authority flip.

The required sequence is:

`D0 review -> I1 Bootstrap/Core authority -> I2 Core semantic/domain migration -> V1 independent broad validation -> G1 integration/authority flip -> semantics-dependent future M10.5`

V1, G1 and later semantics-dependent Kotlin migration remain blocked until separately dispatched and completed.

## Authority disposition through I2

`spec/bootstrap-kernel-v1.json` remains the irreducible host-defined syntax contract. The kernel owns only lexical rules, module/import framing, the uniform declaration envelope, recursive generic `TypeRef` syntax, primitive/list/object literal framing, BodyEntry framing, and `@ModifierCall` tokenization. It contains no domain declaration catalog or domain semantic validation.

`spec/core.aidl` remains the normative source for the Bootstrap/Core meta-model. `spec/core-registry-v1.json` remains its deterministic derived projection.

`spec/core.domain.aidl` is an ordinary AIDL module importing Core. It defines the I2 meta-combinator behavior declarations used by semantic validation, the `primary`/`unique` modifier definitions, and the `entity` declaration contract with `field` and `invariant` BodySlots. Domain rules are therefore data loaded from AIDL rather than parser branches or a host declaration catalog.

`tools/core_semantics.py` interprets those Core-owned contracts. It enforces declaration and slot NamePolicy, Cardinality independently from TypeRef optionality, named argument occurrence, slot occurrence/order/uniqueByName, modifier allowlists/targets/arguments/cardinality, recursive generic TypeRefs, `ref<K>` resolution, and `expression<T>` inference/assignability. Violations produce deterministic `CORE-Sxxx` diagnostics with line/column spans and expected-contract text.

`tools/core_compat.py` is a migration adapter, not a grammar authority. It normalizes representable revision-4 spellings into the Core compatibility representation and emits deterministic semantic hashes. Legacy `[T]` becomes `list<T>`; legacy `T(min..max)` keeps its Core TypeRef plus an explicit lossless range-constraint fact in the compatibility envelope. Representative positional `client ... for ...` and `migration ... from ... to ...` headers normalize to named semantic arguments.

`spec/language-surface-v1.json` revision 4 remains compatibility and migration evidence and remains the production compatibility oracle until G1. It is not allowed to become a second permanent normative grammar.

The machine-readable transition disposition is `spec/core-authority-transition-v1.json`.

## Bootstrap syntax fixed by I1

The declaration envelope remains:

```text
[export] <kind> [<identifier>] [(<named-args>)] [-> <typeRef>] { <body-entries>* }
```

The parser captures a candidate identifier; Core semantics enforces required/optional/forbidden name policy. Header and modifier arguments are named.

`TypeRef` supports qualified names, recursive generics such as `ref<entity>`, `expression<bool>`, `range<int>`, and `list<ref<entity>>`, plus a trailing `?` on a complete TypeRef. Cardinality is separate from TypeRef optionality.

Canonical modifiers begin with `@`. `@name` and `@name(arg: value, ...)` are kernel forms. At body top level the first `@` after a complete balanced value is the hard value/modifier boundary; quoted and nested `@` remains value content.

The three BodyEntry forms remain:

```text
<body-type> [identifier]: [value] [@modifier ...]

<body-type> [identifier]: {
  [value]
  @modifier
}

<body-type> [identifier]: [value] {
  @modifier
}
```

## I2 domain model

The Core-owned `entity` contract requires a declaration identifier. Its repeated `field` slot requires a unique field identifier and accepts either an ordinary `TypeRef` or `ref<entity>`; `@primary` and `@unique` are optional singleton modifiers on fields. Its repeated `invariant` slot has an optional identifier and requires an `expression<bool>` value. Slot ordering metadata keeps fields before invariants in this I2 module.

The `choice`, `ref`, and `expression` semantics used by that contract are declared as AIDL meta-combinators in `core.domain`, and the host semantic engine dispatches by their declared behavior metadata rather than by domain declaration names.

## Scope boundary

I2 does not migrate `core.persistence` or `core.frontend`; does not change Production Normalization or Canonical IR meaning; does not broaden revision-4 production admission; does not run the V1 broad/differential certification; does not perform G1; and does not adapt the already integrated Kotlin `TypeConstruction` slice. PR #88 remains bounded implementation evidence and its generic-TypeRef adaptation belongs after the Core authority gate.

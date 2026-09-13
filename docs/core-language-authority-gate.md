# Core Language Authority Gate

## Status

Phases I1 and I2 are integrated on `main`. Phase V1 is the current independent broad-validation gate and is **not certified**. Broad V1 review found that the I2 semantic registry loader still duplicated part of the Core meta-schema in host code. This focused correction makes normative `spec/core.aidl` own that meta-contract; a fresh independent broad/differential validation of the exact corrected head is still required before V1 may complete.

The required sequence remains:

`D0 review -> I1 Bootstrap/Core authority -> I2 Core semantic/domain migration -> V1 independent broad validation -> G1 integration/authority flip -> semantics-dependent future M10.5`

G1 and later semantics-dependent Kotlin migration remain blocked until V1 is separately certified and the later gates are separately dispatched.

## Authority disposition through V1 correction

`spec/bootstrap-kernel-v1.json` remains the irreducible host-defined syntax contract. The kernel owns only lexical rules, module/import framing, the uniform declaration envelope, recursive generic `TypeRef` syntax, primitive/list/object literal framing, BodyEntry framing, and `@ModifierCall` tokenization. It contains no domain declaration catalog or semantic meta-schema.

`spec/core.aidl` is the normative source for the Bootstrap/Core meta-model. In addition to NamePolicy, Cardinality, TypeRef, ArgumentDefinition, ModifierDefinition, BodySlotDefinition and DeclarationDefinition, it now declares `MetaCombinatorDefinition` plus `SemanticMetaModel`. `SemanticMetaModel` owns the semantic category argument, category-to-definition mapping, and intentionally ignored bootstrap/meta categories. Required fields remain expressed by Core's own `@required` metadata on the relevant definitions.

`spec/core-registry-v1.json` remains a deterministic derived projection of `spec/core.aidl`, not an independent authority. `tools/core_bootstrap.py` regenerates the projection and its exact source hash; both bootstrap tests and the semantic loader fail closed on projection drift.

`spec/core.domain.aidl` remains an ordinary AIDL module importing Core. It defines the I2 meta-combinator behavior declarations used by semantic validation, the `primary`/`unique` modifier definitions, and the `entity` declaration contract with `field` and `invariant` BodySlots. Domain rules remain data loaded from AIDL rather than parser branches or a host declaration catalog.

`tools/core_semantics.py` now loads the exact Core source/projection pair first, derives the accepted semantic category mapping and each meta-definition's field names, requiredness and value types from Core, and then validates semantic modules before interpreting them. ArgumentDefinition, ModifierDefinition, BodySlotDefinition, DeclarationDefinition and MetaCombinatorDefinition all reject undeclared metadata and missing required Core fields deterministically. The host no longer owns a parallel list of those body fields or category strings.

`tools/_core_semantics_runtime.py` contains the existing semantic execution and diagnostic machinery only. It consumes the validated registry and does not contain a registry loader or semantic meta-schema catalog. Existing NamePolicy, Cardinality, named-argument, BodySlot, modifier, recursive TypeRef, `ref<K>` and `expression<T>` behavior is unchanged by this authority correction.

Ordered BodySlots still follow their normative declaration sequence when `ordered: true`; there is no numeric host-only `order` property. Violations continue to produce deterministic `CORE-Sxxx` diagnostics with line/column spans and expected-contract text.

`tools/core_compat.py` remains a migration adapter, not a grammar authority. It normalizes representable revision-4 spellings into the Core compatibility representation and emits deterministic semantic hashes. Legacy `[T]` becomes `list<T>`; legacy `T(min..max)` keeps its Core TypeRef plus an explicit lossless range-constraint fact in the compatibility envelope. Representative positional `client ... for ...` and `migration ... from ... to ...` headers normalize to named semantic arguments.

`spec/language-surface-v1.json` revision 4 remains compatibility and migration evidence and remains the production compatibility oracle until G1. It is not allowed to become a second permanent normative grammar.

The machine-readable transition disposition is `spec/core-authority-transition-v1.json`. It marks D0/I1/I2 complete and V1 as the current phase, but it does not mark V1 complete or perform a project-wide authority flip.

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

The integrated Core-owned `entity` contract requires a declaration identifier. Its repeated `field` slot requires a unique field identifier and accepts either an ordinary `TypeRef` or `ref<entity>`; `@primary` and `@unique` are optional singleton modifiers on fields. Its repeated `invariant` slot has an optional identifier and requires an `expression<bool>` value. Both slots are marked `ordered: true`, so their order is derived from the normative `slots` sequence in the AIDL-authored declaration contract: fields precede invariants.

The `choice`, `ref`, and `expression` semantics used by that contract are declared as AIDL meta-combinators in `core.domain`, and the semantic engine dispatches by their declared behavior metadata rather than by domain declaration names.

## V1 correction and scope boundary

The correction is limited to the authority defect found by broad V1 validation: semantic meta-definition structure must be owned by Core rather than duplicated by the loader. Regression tests cover exact projection consumption, projection drift, Core-owned required/optional fields, Core-owned category mapping, and fail-closed undeclared metadata for ArgumentDefinition, ModifierDefinition, BodySlotDefinition, DeclarationDefinition and MetaCombinatorDefinition while retaining existing I2 behavior.

This correction does not certify V1 by itself. It does not migrate `core.persistence` or `core.frontend`; does not change Production Normalization or Canonical IR meaning; does not broaden revision-4 production admission; does not perform G1; and does not adapt the integrated Kotlin `TypeConstruction` slice. PR #88 remains bounded implementation evidence and generic Core TypeRef adaptation remains deferred until after the Core authority gate.

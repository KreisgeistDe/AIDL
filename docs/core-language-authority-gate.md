# Core Language Authority Gate

## Status

D0, I1, I2 and V1 are complete inputs to the G1 authority-flip candidate. V1 was independently certified on the exact corrected PR #91 head and that correction is integrated on `main` at `f0a8097f926aa9d3940f2684c01b1d66de4dff2a`.

The required sequence remains:

`D0 review -> I1 Bootstrap/Core authority -> I2 Core semantic/domain migration -> V1 independent broad validation -> G1 integration/authority flip -> semantics-dependent future M10.5`

This branch implements G1 but does not claim it is integrated on `main`. Independent exact-head G1 validation and a later separate integration step are still required. Semantics-dependent Kotlin/M10.5 work remains outside this candidate.

## G1 authority disposition

`spec/bootstrap-kernel-v1.json` remains the irreducible host-defined syntax contract. It owns only lexical rules, module/import framing, the uniform declaration envelope, recursive generic `TypeRef` syntax, primitive/list/object literal framing, BodyEntry framing and `@ModifierCall` tokenization. It owns no domain declaration catalog, semantic meta-schema, production admission table or compatibility catalog.

`spec/core.aidl` remains the normative Bootstrap/Core meta-model. `SemanticMetaModel` owns semantic category mapping and meta-contract structure. `spec/core-registry-v1.json` remains a deterministic derived projection of `spec/core.aidl`, never an independent authority, and projection drift remains fail-closed.

`spec/core.domain.aidl` remains an ordinary AIDL module importing Core. It owns the currently accepted domain semantics (`choice`, `ref`, `expression`, `primary`, `unique`, and the `entity` contract) as data rather than parser branches or host declaration catalogs.

G1 adds `spec/core.authority.aidl`, another ordinary Core-authored semantic module. It defines the language contract `compatibilityProjection`: a compatibility artifact must name its source, bind an exact Git-blob SHA-1 and declare its role. `spec/core.compatibility.aidl` is a concrete Core-validated instance binding revision 4 to the exact checked-in `spec/language-surface-v1.json` blob with role `compatibility-only`.

`tools/core_authority.py` validates that Core itself, the deterministic Core projection, the authority module and the compatibility binding are mutually consistent before accepting the revision-4 artifact. It then verifies the exact Git blob identity and frozen M10.1 evidence disposition. Any drift in the legacy JSON without a corresponding Core-authored binding change fails closed.

`tools/compiler_language_surface_body_parity.py` is the production adapter used by Production Normalization. Its constructor now requires the revision-4 artifact to pass `tools/core_authority.py` before the legacy compatibility table can be consumed. The generic `LanguageSurfaceBridge` remains available for compatibility/migration evidence, formatter and differential harnesses, but it is no longer sufficient by itself to authorize production semantic construction.

This is the G1 authority flip: normative Core/Core-authored modules determine permanent semantic authority. Revision-4 JSON can continue to carry frozen compatibility facts and legacy normalization shapes only as an exact Core-authorized projection. It cannot independently change declaration, body-slot, modifier or production semantics after G1.

## Compatibility and production boundary

The legacy parser remains a recognizer for legacy source. G1 does not invent a second parser or remove compatibility syntax. Migration adapters and formatters remain separate from semantic authority.

`tools/core_compat.py` remains deterministic migration evidence. Representable legacy forms continue to converge on the same compatibility facts and semantic hashes: legacy list TypeRefs normalize to Core generics, legacy range constraints remain explicit compatibility facts, and representative client/migration headers normalize deterministically. Unsupported or lossy legacy shapes remain fail-closed.

`spec/language-surface-v1.json` revision 4 remains frozen M10.1 compatibility/migration evidence. Its former pre-G1 role as an independent production compatibility oracle is ended by G1. Production may still consume its exact data only through the Core-authored compatibility binding; changing the artifact alone is rejected before normalization.

The existing Production Normalization and Canonical IR semantic envelope is not broadened by this phase. Existing admitted/fail-closed dispositions remain intact. G1 changes the authority source, not the language meaning or admission set.

## Preserved I1/I2/V1 semantics

The declaration envelope remains:

```text
[export] <kind> [<identifier>] [(<named-args>)] [-> <typeRef>] { <body-entries>* }
```

Core continues to own NamePolicy, Cardinality, ArgumentDefinition, ModifierDefinition, BodySlotDefinition, DeclarationDefinition and MetaCombinatorDefinition. The semantic loader remains Core-derived and validates all required meta-contract families before interpretation; undeclared or missing metadata fails closed.

`TypeRef` continues to support recursive generics and trailing optionality. Cardinality remains independent of TypeRef optionality. `ref<K>` and `expression<T>` remain Core-declared combinator behavior. Diagnostics remain deterministic, sorted and source-spanned.

Ordered BodySlots still derive solely from the normative `DeclarationDefinition.slots` sequence filtered by `ordered: true`. There is no numeric host-only `order` property.

`tools/_core_semantics_runtime.py` remains loader/meta-schema free. It executes already validated Core contracts and dispatches combinator behavior from the validated registry; it does not own a parallel semantic catalog.

## Scope boundary

This G1 candidate changes only authority plumbing, durable transition state, focused tests and the exhaustive committed-source classification needed for the two new Core AIDL modules. It does not add project `.ai/**`, introduce new language semantics, widen Canonical IR meaning, change production admission, or perform semantics-dependent Kotlin/M10.5 adaptation.

After independent validation and later integration of this exact candidate, semantics-dependent M10.5 may be separately reconsidered under Core-owned authority. That later work remains a distinct dispatch and must not be inferred from this candidate alone.

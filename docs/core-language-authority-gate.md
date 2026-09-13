# Core Language Authority Gate

## Status

D0, I1, I2, V1 and G1 are complete and integrated. V1 was independently certified on the exact corrected PR #91 head and integrated on `main` at `f0a8097f926aa9d3940f2684c01b1d66de4dff2a`; G1 was independently validated on PR #92 and integrated on `main` at `b90c44912d7f82450c2190473035bce14bef828d`.

The completed sequence is:

`D0 review -> I1 Bootstrap/Core authority -> I2 Core semantic/domain migration -> V1 independent broad validation -> G1 integration/authority flip`

Normative Core/Core-authored modules are now the sole permanent semantic authority. The next dependency-ready roadmap gate is the separately dispatched M10.5-01 parity-baseline refresh; M10.5-02 and later semantics-dependent Kotlin work remain blocked until Gate 01 is durably completed.

## G1 authority disposition

`spec/bootstrap-kernel-v1.json` remains the irreducible host-defined syntax contract. It owns only lexical rules, module/import framing, the uniform declaration envelope, recursive generic `TypeRef` syntax, primitive/list/object literal framing, BodyEntry framing and `@ModifierCall` tokenization. It owns no domain declaration catalog, semantic meta-schema, production admission table or compatibility catalog.

`spec/core.aidl` remains the normative Bootstrap/Core meta-model. `SemanticMetaModel` owns semantic category mapping and meta-contract structure. `spec/core-registry-v1.json` remains a deterministic derived projection of `spec/core.aidl`, never an independent authority, and projection drift remains fail-closed.

`spec/core.domain.aidl` remains an ordinary AIDL module importing Core. It owns the currently accepted domain semantics (`choice`, `ref`, `expression`, `primary`, `unique`, and the `entity` contract) as data rather than parser branches or host declaration catalogs.

G1 added `spec/core.authority.aidl`, another ordinary Core-authored semantic module. It defines the language contract `compatibilityProjection`: a compatibility artifact must name its source, bind an exact Git-blob SHA-1 and declare its role. `spec/core.compatibility.aidl` is a concrete Core-validated instance binding revision 4 to the exact checked-in `spec/language-surface-v1.json` blob with role `compatibility-only`.

`tools/core_authority.py` validates that Core itself, the deterministic Core projection, the authority module and the compatibility binding are mutually consistent before accepting the revision-4 artifact. It then verifies the exact Git blob identity and frozen M10.1 evidence disposition. Any drift in the legacy JSON without a corresponding Core-authored binding change fails closed.

`tools/compiler_language_surface_body_parity.py` is the production adapter used by Production Normalization. Its constructor requires the revision-4 artifact to pass `tools/core_authority.py` before the legacy compatibility table can be consumed. The generic `LanguageSurfaceBridge` remains available for compatibility/migration evidence, formatter and differential harnesses, but it is not sufficient by itself to authorize production semantic construction.

This is the integrated G1 authority flip: normative Core/Core-authored modules determine permanent semantic authority. Revision-4 JSON can continue to carry frozen compatibility facts and legacy normalization shapes only as an exact Core-authorized projection. It cannot independently change declaration, body-slot, modifier or production semantics after G1.

## Compatibility and production boundary

The legacy parser remains a recognizer for legacy source. G1 does not invent a second parser or remove compatibility syntax. Migration adapters and formatters remain separate from semantic authority.

`tools/core_compat.py` remains deterministic migration evidence. Representable legacy forms continue to converge on the same compatibility facts and semantic hashes: legacy list TypeRefs normalize to Core generics, legacy range constraints remain explicit compatibility facts, and representative client/migration headers normalize deterministically. Unsupported or lossy legacy shapes remain fail-closed.

`spec/language-surface-v1.json` revision 4 remains frozen M10.1 compatibility/migration evidence. Its former pre-G1 role as an independent production compatibility oracle ended with G1. Production may still consume its exact data only through the Core-authored compatibility binding; changing the artifact alone is rejected before normalization.

The existing Production Normalization and Canonical IR semantic envelope was not broadened by G1. Existing admitted/fail-closed dispositions remain intact. G1 changed the authority source, not the language meaning or admission set.

## Preserved I1/I2/V1 semantics

The declaration envelope remains:

```text
[export] <kind> [<identifier>] [(<named-args>)] [-> <typeRef>] { <body-entries>* }
```

Core continues to own NamePolicy, Cardinality, ArgumentDefinition, ModifierDefinition, BodySlotDefinition, DeclarationDefinition and MetaCombinatorDefinition. The semantic loader remains Core-derived and validates all required meta-contract families before interpretation; undeclared or missing metadata fails closed.

`TypeRef` continues to support recursive generics and trailing optionality. Cardinality remains independent of TypeRef optionality. `ref<K>` and `expression<T>` remain Core-declared combinator behavior. Diagnostics remain deterministic, sorted and source-spanned.

Ordered BodySlots still derive solely from the normative `DeclarationDefinition.slots` sequence filtered by `ordered: true`. There is no numeric host-only `order` property.

`tools/_core_semantics_runtime.py` remains loader/meta-schema free. It executes already validated Core contracts and dispatches combinator behavior from the validated registry; it does not own a parallel semantic catalog.

## Post-G1 roadmap boundary

The Core Language Authority Gate is complete. M10.5-01 is the next dependency-ready gate and must refresh/reconcile the Python parity baseline and differential harness against the post-G1 Core-owned authority and current Python reference state. PR #77 is already-merged historical/provisional M10.5-01 parity evidence on main via `1574963eed95a2f80c1cdc47f48a3eaa39df4a4b`; it is not a pending integration target and does not by itself satisfy the post-G1 current-main Gate 01 refresh/revalidation requirement.

A separate current-main M10.5-01 refresh/revalidation package now exists as an implementation candidate derived from `main@f471fd9c1ee808ff9557d4a9f6bdf8b092d9c2c5`. Its parity fingerprint binds the normative Core source, Core-authored compatibility contract/binding, current Python reference/conformance evidence and the existing IR/profile/M10.2/M10.3 contracts. It remains non-normative and requires fresh independent exact-head validation and later integration before Gate 01 is complete.

M10.5-02 and later Kotlin work remain dependent on durable acceptance of that post-G1 Gate 01 package. No semantics-dependent Kotlin adaptation, parser/type semantic change, Canonical IR widening, production-admission change, Bootstrap Kernel change, Core registry semantic change or revision-4 compatibility-content change is part of this Gate-01 refresh.

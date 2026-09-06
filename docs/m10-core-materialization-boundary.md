# M10-04 Core materialization boundary

M10-04 closes a compiler/Canonical-IR gap without expanding AIDL's supported
language surface.

The parser is intentionally broader than the currently supported Core semantic
model. Parser acceptance alone therefore remains insufficient evidence that a
construct is supported. The remaining silent-drop risk is a **resolved** Core
fact whose syntax and name resolution succeed even though the current
Canonical IR cannot preserve its meaning.

The compiler now reports stable `AIDL-T005` errors for that boundary:

- a nominal type that resolves to a declaration kind which is not a materialized
  Core type;
- an entity identity type whose resolved target is not an entity;
- a project generic declaration or project generic type use whose type-parameter
  semantics are parsed but are not represented by current Canonical IR.

Unresolved Core names are not diagnosed again by M10-04: existing `AIDL-R003`
resolution diagnostics remain authoritative and avoid cascaded errors. Existing
query/mutation error-name contracts are also preserved; external or profile
error names are not reclassified as Core materialization failures.

`AIDL-T005` is source-located and compiler-owned. It is emitted in the type
phase only after the existing parse/import/duplicate-declaration blockers are
clear and only for facts that successfully resolve, so it does not replace
parser, resolver, or earlier policy diagnostics. Standard Core nominal types
remain explicit contracts rather than inferred support for arbitrary names.

This boundary does **not** promote wider profile syntax, generic semantics,
workflow/runtime behavior, UI, offline, media, cloud, or realtime constructs.
Those surfaces remain governed by their existing conformance status and later
roadmap items. The rule is only that a resolved Core semantic fact cannot be
silently discarded or widened on its way to Canonical IR.

Executable evidence lives in `tools/compiler_core_materialization.py` and the
existing conformance-tracked `tools/test_core_typecheck.py` suite. The latter
covers the `AIDL-T005` negative cases, preserves existing `AIDL-R003` and
external/profile-error behavior, and checks Petstore, Calendar Offline, and
VideoHub deterministically. `spec/core-conformance.json` therefore keeps its
existing `validate-core`/`validate-types` evidence IDs and layer statuses rather
than inventing a new support claim solely for M10-04.

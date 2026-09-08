# M10 Core Module/Import claim-model closure

This closure changes only the Core Module validation boundary and the Module/Import layer-applicability model. It does not add source syntax, standalone Canonical-IR nodes, runtime behavior, generators, IDE support, App work, M11 work, M10.5/Kotlin work, M16.5 work, release/protection work, or project `.ai/**` state.

## Module validation

A source file may contain at most one `module` declaration, and that declaration must precede every import or other declaration in the same file. `tools/compiler_module_validation.py` now converts the parser-preserved top-level order into stable source-located `AIDL-R003` diagnostics for a second module declaration and for any module declaration that appears after an import or declaration.

Resolved module dependencies remain derived by `tools/compiler_project.py`. Its deterministic `module_cycles` strongly connected components are now surfaced as source-located `AIDL-R004` diagnostics anchored to the first deterministic participating resolved import edge. Both direct self-cycles and multi-module cycles are rejected before Canonical IR. Existing `AIDL-R001` ownership for unresolved explicit or wildcard imports and `AIDL-R002` ownership for duplicate declarations are unchanged.

`tools/test_core_module_import_claim_model.py` proves the accepted and rejected boundaries directly. A leading module with explicit and wildcard imports resolves without validation errors; explicit and wildcard imports that reach the same exported declaration preserve the same resolved FQN and downstream declaration identity. Repeated builds are deterministic and the resulting full document validates against `spec/ir.schema.json`. Negative cases cover duplicate and late modules, unresolved explicit and wildcard imports, and direct and multi-module cycles with stable source locations.

## Layer applicability

`decl.module/validate` is now `implemented` because the complete Core Module validation boundary is executable: one-module-per-file, leading placement, and cyclic-module rejection are all enforced with deterministic diagnostics.

`decl.import/validate` is `not-applicable`. Import directives are compile-time namespace-resolution syntax in Core. Explicit/wildcard resolution and unresolved-import failure belong to Resolve, and there is no independent Import Validate rule. In particular, this closure does not invent an import-before-declaration rule.

`decl.module/ir` and `decl.import/ir` are both `not-applicable`. Canonical IR intentionally contains semantic declaration identities and resolved references rather than source Module/Import directives. Module ownership is preserved in every emitted declaration through `ownerModule`, `fqn`, and `declarationId`; equivalent explicit and wildcard imports resolve to the same downstream target identity. No standalone Module or Import IR form is required or introduced.

These status corrections add `decl.module` and `decl.import` to the derived Core Supported fixture set because their Parse/Resolve/Validate/IR boundaries are now entirely `implemented` or semantically `not-applicable`, with executable evidence for every applicable layer.

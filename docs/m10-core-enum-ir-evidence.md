# M10 Core enum IR evidence

This focused M10 closure records executable Canonical-IR evidence for the already accepted Core enum semantic contract.

The Core subset already accepts enum declarations. `tools/compiler_ir.py` materializes an enum declaration with stable declaration identity and the source case sequence as `values`; `spec/ir.schema.json` requires a non-empty, unique string list for that field.

`tools/test_core_enum_ir_semantics.py` extends the existing valid M4 minimal source with `SnapshotState { Draft Published Archived }`, builds Canonical IR twice, and proves deterministic preservation of enum identity and case ordering. The emitted document is validated against the closed IR schema.

Negative executable evidence mutates only emitted IR and proves that the closed schema rejects a missing `values` field, an empty case list, and duplicate cases.

This closure does not promote `decl.enum/ir`: it proves the enum identity/case-list semantic fact, while `decl.enum` still has independent partial Validate/IR/Generate coverage that has not been exhaustively closed as a whole declaration cell. M10 acceptance criteria 1 and 3 therefore remain open; criteria 2 and 4 remain complete. No syntax, language semantics, generator behavior, IDE support, Ruleset, tag, release, or project `.ai/**` path is changed.

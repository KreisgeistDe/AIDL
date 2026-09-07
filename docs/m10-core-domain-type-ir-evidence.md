# M10 Core domain-type IR evidence

This focused M10 closure records executable Canonical-IR evidence for two already accepted Core domain type declarations: `alias` and `opaque`.

The Core subset already accepts both declarations. Canonical IR materializes an alias's referenced type as `target` and an opaque type's underlying representation as `representation`; both values use the closed `typeRef` contract from `spec/ir.schema.json`.

`tools/test_core_domain_type_ir_semantics.py` extends the existing valid M4 minimal source with `SnapshotLabel = string` and `SnapshotToken = uuid`, builds Canonical IR twice, and proves that the semantic alias and opaque declaration objects are deterministic. The test also validates the complete emitted document against the closed IR schema.

Negative evidence mutates only the emitted IR and proves that the closed schema rejects a missing alias target, a malformed set target, a missing opaque representation, and a malformed map representation.

This closure does not promote `decl.alias/ir` or `decl.opaque/ir`: it proves the target/representation semantic subset, not every Validate/IR/Generate behavior for those declaration classes. M10 acceptance criteria 1 and 3 therefore remain open; criteria 2 and 4 remain complete. No syntax, language semantics, generator behavior, IDE support, Ruleset, tag, release, or project `.ai/**` path is changed.

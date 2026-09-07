# M10 Core Value Canonical IR Evidence

This closure records focused executable evidence for already accepted Core `value` field semantics without promoting the full `decl.value/ir` matrix cell.

`tools/test_core_value_ir_semantics.py` proves that Canonical IR preserves Value field source order, recursively materialized field types, nullability-derived `required`, and the existing `mutable`, `sensitive`, and `generated` metadata when those modifiers are materialized independently. The test also validates the complete emitted IR document against the closed `spec/ir.schema.json` contract.

Negative executable evidence is schema-owned: regressions reject missing required field metadata, malformed metadata types, missing field types, and malformed nested typeRef shapes.

Rest-gap review found a separate accepted combination that is not yet correctly materialized: a nullable field followed by a modifier, for example `string? sensitive`, is currently conflated by IR type/modifier splitting. That gap is intentionally not hidden or promoted by this closure and is one reason `decl.value/ir` remains `partial` alongside unrelated Validate/Generate/IDE gaps.

M10 acceptance criteria 1 and 3 therefore remain open; criteria 2 and 4 remain complete.

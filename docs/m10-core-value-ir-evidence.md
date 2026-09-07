# M10 Core Value Canonical IR Evidence

This closure records focused executable evidence for the already accepted Core `value` field contract without promoting the full `decl.value/ir` matrix cell.

`tools/test_core_value_ir_semantics.py` proves that Canonical IR preserves Value field source order, recursively materialized field types, nullability-derived `required`, and the existing `mutable`, `sensitive`, and `generated` metadata. The test also validates the complete emitted IR document against the closed `spec/ir.schema.json` contract.

Negative executable evidence is schema-owned: regressions reject missing required field metadata, malformed metadata types, missing field types, and malformed nested typeRef shapes. This block does not claim a new Value-specific source diagnostic beyond the compiler validation already represented by the existing partial Validate status.

This is a bounded Canonical-IR semantic-fact closure. `decl.value` remains `partial` for Validate, IR, Generate, and IDE because unrelated declaration behavior still requires independent closure. M10 acceptance criteria 1 and 3 therefore remain open; criteria 2 and 4 remain complete.

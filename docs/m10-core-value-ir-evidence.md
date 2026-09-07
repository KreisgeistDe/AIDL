# M10 Core Value Canonical IR Evidence

This closure records focused executable evidence for the already accepted Core `value` field contract without promoting the full `decl.value/ir` matrix cell.

`tools/test_core_value_ir_semantics.py` proves that Canonical IR preserves Value field source order, recursively materialized field types, nullability-derived `required`, and the existing `mutable`, `sensitive`, and `generated` metadata. The test also validates the complete emitted IR document against the closed `spec/ir.schema.json` contract.

Negative evidence uses the existing compiler-owned Core type checker to reject an invalid Value field map key with `AIDL-T001` before IR emission. Additional schema regressions reject missing required field metadata, malformed metadata types, missing field types, and malformed nested typeRef shapes.

This is a bounded Canonical-IR semantic-fact closure. `decl.value` remains `partial` for Validate, IR, Generate, and IDE because unrelated declaration behavior still requires independent closure. M10 acceptance criteria 1 and 3 therefore remain open; criteria 2 and 4 remain complete.

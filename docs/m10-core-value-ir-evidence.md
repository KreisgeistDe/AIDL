# M10 Core Value Canonical IR Evidence

This closure records focused executable evidence for already accepted Core `value` field semantics without promoting the full `decl.value/ir` matrix cell.

`tools/test_core_value_ir_semantics.py` proves that Canonical IR preserves Value field source order, recursively materialized field types, nullability-derived `required`, and the existing `mutable`, `sensitive`, and `generated` metadata. The focused regression now also covers the previously broken coexistence of a complete type expression with following field modifiers: `string? sensitive`, `set<string> required`, and a nested nullable `map<string, set<uuid?>?>? generated` all retain both their full type shape and modifier metadata.

The IR fix is intentionally narrow: `_take_type` now finds the type/modifier boundary on the original field text and leaves type-spacing normalization to `_type` after the type expression has been isolated. Compiler-owned Core type checking, syntax, language semantics, generators, and IDE behavior are unchanged.

Negative executable evidence remains schema-owned: regressions reject missing required field metadata, malformed metadata types, missing field types, and malformed nested typeRef shapes.

A full rest-gap review does not justify promoting `decl.value/ir`: the wider language documentation permits additional Value declaration semantics outside the currently proven Core IR contract, including generic Value declarations, while the Core matrix still records independent Validate/Generate/IDE gaps. This fix therefore removes the documented type-plus-modifier defect without claiming whole-cell completeness.

M10 acceptance criteria 1 and 3 remain open; criteria 2 and 4 remain complete.

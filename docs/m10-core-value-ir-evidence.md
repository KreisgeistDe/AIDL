# M10 Core Value Canonical IR Evidence

This closure records focused executable evidence for already accepted Core `value` field semantics without promoting the full `decl.value/ir` matrix cell.

`tools/test_core_value_ir_semantics.py` proves that Canonical IR preserves Value field source order, recursively materialized field types, nullability-derived `required`, and the existing `mutable`, `sensitive`, and `generated` metadata. The focused regression now also covers the previously broken coexistence of a complete type expression with following field modifiers: `string? sensitive`, `set<string> required`, a constrained `string(1..80) required mutable`, and a nested nullable `map<string, set<uuid?>?>? generated` all retain both their full type shape and modifier metadata.

The IR fix is intentionally narrow: `_take_type` finds the type/modifier boundary on the original field text by recognizing existing field modifiers at top level, and `_type` normalizes the complete isolated type expression, including parser whitespace around constructor delimiters and constrained scalar parentheses. Compiler-owned Core type checking, syntax, language semantics, generators, and IDE behavior are unchanged.

The existing M4/Petstore golden fixtures are refreshed only where the corrected Canonical IR now preserves the already accepted `string(1..80)` constraints through semantic hashes, plans, and the unchanged PostgreSQL generator's existing constraint emission. No generator code or generator support claim changes in this fix.

Negative executable evidence remains schema-owned: regressions reject missing required field metadata, malformed metadata types, missing field types, and malformed nested typeRef shapes.

A full rest-gap review does not justify promoting `decl.value/ir`: the wider language documentation permits additional Value declaration semantics outside the currently proven Core IR contract, including generic Value declarations, while the Core matrix still records independent Validate/Generate/IDE gaps. This fix therefore removes the documented type-plus-modifier defect without claiming whole-cell completeness.

M10 acceptance criteria 1 and 3 remain open; criteria 2 and 4 remain complete.

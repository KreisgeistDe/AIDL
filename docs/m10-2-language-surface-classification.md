# M10.2 Language Surface Classification

M10.2 makes repository source and documentation auditable against frozen M10.1 revision 4 without changing parser, compiler, runtime, Canonical IR, or production-admission semantics.

The machine-readable authority for this inventory is `spec/m10-2-language-surface-classification.json`; `tools/m10_2_language_surface_classification.py` verifies it against the repository tree and frozen contract.

## Support tiers

Every committed AIDL source and every required syntax/semantic documentation surface is classified as exactly one of five tiers:

1. **production-admitted canonical** — canonical target representation with current certified Production Normalization support;
2. **canonical-but-not-yet-admitted** — canonical target representation frozen by revision 4 but not currently production-admitted;
3. **legacy-readable compatibility** — historical source intentionally readable for compatibility/migration but not the target grammar;
4. **negative/rejection fixture** — source whose expected rejection or diagnostics are the evidence;
5. **illustrative/aspirational** — explanatory/specification material that does not independently claim current production admission.

Parser readability, canonical target syntax, production semantic admission, runnable/generated support, compatibility readability, and expected rejection are therefore separate properties. A file appearing in a reference application or a valid parser fixture is not sufficient evidence that every construct in that file is production-admitted.

## Current committed-source disposition

All three reference applications (`examples/calendar-offline`, `examples/petstore`, and `examples/videohub`) remain **legacy-readable compatibility** during M10.2. Their executable migration to the unified target grammar is intentionally deferred to M10.3.

`fixtures/invalid/**` and `tools/m2_semantic_fixtures/**` are **negative/rejection fixture** evidence. `fixtures/valid/**` remains **legacy-readable compatibility** evidence because those fixtures establish current parser/toolchain behavior, not an independent canonical-production support claim.

The validator discovers every committed `*.aidl` file recursively and requires exactly one matching source-classification rule. A new source outside the classified corpus, or a source matched by more than one rule, fails closed.

## Documentation disposition

`docs/06-grammar.md` is the normative human-readable projection of the frozen canonical target grammar. It deliberately excludes historical parser special cases from the normative grammar and isolates them as non-canonical compatibility input.

The overview/core/diagnostics/evolution/reference documents and example READMEs remain classified explicitly because they contain broad specified-language or product-story material that can exceed current production admission. Their examples and descriptions must be read through the support-tier model above; M10.1 revision 4, its certification, and current Production Normalization remain the support authority.

The validator also discovers Markdown files containing explicit AIDL/EBNF fenced syntax. Such a document must be present in the classification manifest; otherwise validation fails closed. This prevents newly added syntax documentation from silently bypassing M10.2 classification.

## M10.3 mismatch handoff

M10.2 does not mass-migrate reference source. The remaining mismatch set is intentionally narrow and explicit:

- reference applications and compatibility fixtures still contain historical spellings and declaration families that must be migrated or deliberately retained as compatibility/non-production evidence;
- broad overview/reference material describes language families beyond the ten M10.1-certified production-admitted declaration families;
- any desired reference behavior that truly requires new Python semantics or production admission must use a separately versioned contract update, re-freeze, exhaustive coverage, and certification before admission.

Those executable migration and semantic-disposition decisions belong to M10.3. M10.5 remains blocked until integrated M10.3, and pre-M10.2 PR #77 remains provisional evidence only.

## Deterministic enforcement

Run:

`python3 -m tools.m10_2_language_surface_classification`

Focused regressions in `tools/test_m10_2_language_surface_classification.py` prove deterministic output and fail-closed behavior for unclassified source, duplicate classification, documentation-index drift, and frozen-contract revision drift. The generic Python CI selector discovers these tests automatically.

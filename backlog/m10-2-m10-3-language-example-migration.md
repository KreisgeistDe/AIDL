# M10.2–M10.3 — Pre-Kotlin Language and Example Migration Gates

## Purpose

M10.2 and M10.3 are narrow pre-M10.5 readiness gates between the completed M10.1 frozen language authority and the Kotlin compiler migration. They do not renumber M10.5, do not replace later M16.5 normalization/metamodel work, and do not themselves authorize grammar, compiler, runtime, Canonical-IR, generator, IDE, or Kotlin implementation changes.

The durable order is:

`M10.1 -> M10.2 -> M10.3 -> refreshed M10.5-01 -> M10.5-02 and later Kotlin work`.

M10.1 remains the frozen semantic authority until an explicitly versioned contract change is reviewed, re-frozen, exhaustively covered, and certified. M16.5 remains the later broader language-surface normalization/metamodel milestone; it is not a substitute for these narrower source/documentation/example readiness gates.

## M10.2 — Canonical Language Documentation & Source Migration Gate

M10.2 consumes the completed M10.1 revision-4 Production Semantic Envelope and makes the repository's source and documentation surface auditable against it before any final cross-language parity baseline is frozen.

- [x] **M10.2-01 — Classify and migrate the canonical language documentation and committed source surface.** **P1**

### Required scope

M10.2 implementation must exhaustively inventory every committed AIDL source and every documented syntax surface, including all three reference applications and all committed valid, compatibility, semantic-conformance, negative, rejection, and illustrative fixtures. Each source or documentation occurrence must be classified as exactly one of:

1. production-admitted canonical form;
2. canonical-but-not-yet-admitted form;
3. legacy-readable compatibility form;
4. negative/rejection fixture; or
5. illustrative/aspirational material.

The implementation must align `docs/06-grammar.md` plus relevant overview, core, diagnostics, evolution, and reference material to the frozen unified target design. Normative target-language documentation must not retain contradictory legacy syntax as though it were canonical. Compatibility syntax may remain documented only when it is explicitly labeled as compatibility-only and is not confused with production admission.

Reference-application and fixture documentation must distinguish parser readability, production semantic admission, runnable/generated support, compatibility-only acceptance, and expected rejection. Newly added grammar/source/documentation surfaces that are not classified must fail closed in deterministic CI checks.

M10.2 is not a semantic-widening milestone. If the inventory exposes a desired form that is not admitted by the current Python reference Production Semantic Envelope, M10.2 records the mismatch for M10.3; it does not silently expand support.

### M10.2 completion gate

M10.2 is complete through `spec/m10-2-language-surface-classification.json`, `tools/m10_2_language_surface_classification.py`, focused negative regressions, the revision-4-aligned `docs/06-grammar.md`, explicit support-tier updates in core/diagnostics/overview/reference material and all three reference-app READMEs, and the M10.3 mismatch handoff in `docs/m10-2-language-surface-classification.md`. Every committed `.aidl` file must match exactly one source rule, every discovered AIDL/EBNF documentation surface must be classified, and contract/classification drift fails closed. No reference-app `.aidl`, parser/compiler/runtime/Canonical-IR behavior, or frozen M10.1 semantic contract was changed.

## M10.3 — Reference Example & Production Semantic Closure Gate

M10.3 depends on completed M10.2. It resolves the classified mismatches needed for the intended reference examples and production story before any Kotlin parity baseline is considered final.

- [ ] **M10.3-01 — Migrate intended reference examples and close production semantic mismatches.** **P1**

### Required scope

M10.3 must migrate every intended reference example to the unified target grammar and resolve every grammar/design/example mismatch explicitly. Negative/rejection fixtures and legacy-readable compatibility fixtures remain intentionally classified and must not be converted into false positive production evidence.

Every mismatch discovered by M10.2 receives one explicit disposition:

- migrate the example/documentation to an already admitted canonical form;
- classify the surface as intentionally non-production/fail-closed; or
- if the product requirement genuinely needs new Python reference semantics or production admission, make a separately versioned contract update, re-freeze it, and rerun the complete coverage/certification gates before claiming admission.

Required diagnostics, semantics, and example explanations must agree. Executable deterministic grammar-to-examples conformance checks must cover all three reference applications and the committed fixture classes and must fail closed on newly inconsistent surfaces.

### M10.3 completion gate

M10.3 completes only after all M10.2 mismatches are explicitly resolved, intended reference examples use the unified target grammar, negative and compatibility fixtures remain explicitly classified, grammar/example conformance is deterministic, and any semantic/admission change has gone through a versioned re-freeze and certification rather than implicit widening.

## M10.5 handoff

The whole M10.5 Kotlin migration depends on integrated M10.3. The current pre-M10.2 M10.5-01 work and PR #77 are provisional/deferred evidence only and cannot serve as the final Kotlin parity baseline.

After M10.3 is integrated, M10.5-01 must be refreshed or rebased against the resulting Python reference baseline, its complete evidence inventory must be regenerated, and its deterministic fingerprint must be recomputed before M10.5-02 may begin. No Kotlin semantic implementation is authorized by M10.2 or M10.3.

# M10 Core executable evidence

The Core conformance matrix remains authoritative for Parse, Resolve, Validate, IR, Generate, and IDE status. Status promotion is allowed only when the repository contains executable evidence for the complete claimed layer behavior; evidence must not manufacture support that the implementation does not provide.

`spec/core-executable-evidence.json` is a deterministic companion registry for cells marked `implemented` in `spec/core-conformance.json`. A matrix cell reaches the executable-evidence gate only when at least one of its existing `layerEvidence` IDs resolves through the companion registry to a committed focused test file. `python3 -m tools.core_executable_evidence validate` checks that chain offline and rejects unknown, stale, missing, unsorted, or non-test evidence.

The registry deliberately reuses existing executable regressions where they exercise the claimed layer:

- Parse: `tools/test_aidl_parser.py`
- Resolve: `tools/test_compiler_project.py`
- Validate: `tools/test_m5_fixture_corpus.py` and `tools/test_core_typecheck.py`
- Canonical IR: `tools/test_aidl_ir.py`, `tools/test_core_transaction_semantics.py`, and `tools/test_ir_schema.py`
- Generate: `tools/test_core_transaction_semantics.py` and `tools/test_m4_petstore.py`

## Transaction resource/outbox closure

The Core transaction contract already requires one transaction resource owner and transactional event publication through an outbox. Canonical IR preserves the selected resource as `rootEffect.resourceId` and preserves transactional publication as a `publish` step with `via: outbox`. The PostgreSQL transaction generator resolves that exact resource, rejects an unresolved resource, requires canonical outbox publication, emits the outbox insert as a transaction step, and commits only after all steps have executed.

`tools/test_core_transaction_semantics.py` binds those existing semantics end to end through the Petstore reference source. It proves both canonical IR facts, proves that the PostgreSQL generator consumes the same resource and outbox step inside its generated transaction, and proves negative rejection for an unresolved transaction resource and a non-outbox publish. This justifies promoting only these four cells from `partial` to `implemented`:

- `rule.transaction.resource-owner`: IR and Generate
- `rule.transaction.outbox-atomic`: IR and Generate

No source syntax, language semantic, support surface, or IDE status is widened by this closure.

No IDE cell is currently marked `implemented`, so the registry does not manufacture IDE completeness from workflow or documentation evidence. The same rule applies to every remaining `partial` or `missing` cell in any layer: executable tests may exist for a subset of behavior, but status remains open until the matrix can truthfully claim layer completeness.

This transaction block measurably reduces the first M10 acceptance gap by four partial layer cells and the third acceptance gap by preserving two required transaction semantic facts in Canonical IR. Neither acceptance criterion is complete: other Core matrix cells remain `partial` or `missing`, including unrelated IR and generator capabilities that require independent implementation or narrower claim decisions before promotion.

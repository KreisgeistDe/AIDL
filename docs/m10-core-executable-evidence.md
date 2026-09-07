# M10 Core executable evidence

The Core conformance matrix remains authoritative for Parse, Resolve, Validate, IR, Generate, and IDE status. This document does not promote any matrix status.

`spec/core-executable-evidence.json` is a deterministic companion registry for cells already marked `implemented` in `spec/core-conformance.json`. A matrix cell reaches the executable-evidence gate only when at least one of its existing `layerEvidence` IDs resolves through the companion registry to a committed focused test file. `python3 -m tools.core_executable_evidence validate` checks that chain offline and rejects unknown, stale, missing, unsorted, or non-test evidence.

The registry deliberately reuses existing executable regressions where they already exercise the claimed layer:

- Parse: `tools/test_aidl_parser.py`
- Resolve: `tools/test_compiler_project.py`
- Validate: `tools/test_m5_fixture_corpus.py` and `tools/test_core_typecheck.py`
- Canonical IR: `tools/test_aidl_ir.py` and `tools/test_ir_schema.py`
- Generate: `tools/test_m4_petstore.py`

No IDE cell is currently marked `implemented`, so the registry does not manufacture an IDE-completeness claim from workflow or documentation evidence. The same rule applies to every `partial` or `missing` cell in any layer: executable tests may exist for a subset of behavior, but status remains open until the matrix can truthfully claim layer completeness.

Therefore this block closes the evidence-quality gap for existing `implemented` Core cells, but it does not by itself complete the M10 acceptance criterion that every Core support claim has executable evidence in every required implementation layer. The remaining acceptance gap is exactly the set of matrix cells still marked `partial` or `missing`; those require independent implementation or narrower claim decisions before they can be promoted.

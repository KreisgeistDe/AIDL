# M10.5 Python Reference Contract

M10.5-01 freezes the observable Python-reference evidence needed for later differential migration work. It does **not** define language semantics, widen support, change Canonical IR, or implement Kotlin compiler behavior. Normative language meaning remains owned by frozen M10.1 revision 4 in `spec/language-surface-v1.json`.

The machine-readable inventory is `tools/m10_5_reference_contract.json`; `tools/m10_5_reference_contract.py` validates it and emits deterministic evidence hashes plus a whole-contract fingerprint. The inventory references existing compiler/parser/type/diagnostic, Production Normalization, Canonical-IR/compatibility, CLI/semantic-query, fixture/reference-application, and CI evidence. It deliberately records file identities rather than copying grammar, declaration, type, diagnostic, or IR rules into a second semantic table.

## Differential contract

Later Python-versus-Kotlin execution uses the same source/config/profile inputs and compares canonical structured output exactly across accepted/rejected classification, diagnostics, Canonical IR, stable identities, ordering, source locations, and exit behavior. M10.5-01 permits no transport-only semantic normalization: `transport_only_differences` is empty. Any future exception requires an explicit reviewed contract change rather than being silently ignored by a comparator.

The contract names both future runner implementations (`python`, `kotlin`) but explicitly states that Kotlin is not required by M10.5-01. M10.5-02 and later packages remain responsible for implementation. This package therefore establishes the oracle and comparison boundary without starting migration.

## Parity corpus and fingerprints

Existing committed Golden Fixture/compatibility tests and Petstore reference applications are inventory evidence; no new support claim is inferred from their presence. Each evidence file is SHA-256 fingerprinted. The frozen M10.1 contract is fingerprinted separately, and the deterministic aggregate fingerprint also covers the inventory schema and differential comparison contract. Missing evidence, project `.ai/**` references, surface-set drift, frozen-contract identity drift, comparator drift, or a change that makes this inventory normative fails closed.

The generic Python CI selector discovers `tools/test_m10_5_reference_contract.py`. Its negative regressions prove that schema, surface, frozen-contract, comparison-dimension, transport-exception, missing-file, and project-`.ai` drift are rejected.

## Boundary to later phases

M10.5-02 remains open for the Kotlin Multiplatform skeleton and deterministic cross-implementation utilities. M10.5-03 remains open for bounded front-end parity slices. Neither package is implemented or marked complete by M10.5-01. Python remains the reference/conformance implementation until the separately defined M10.5 exit criteria are satisfied.

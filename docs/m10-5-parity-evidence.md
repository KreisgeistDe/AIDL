# M10.5-01 refreshed Python parity evidence

M10.5-01 is refreshed only after integrated M10.3. This document describes the
candidate Python reference/conformance baseline built from
`main@cbe34ce18dfa696c3bcbf30b6b37af53989112d6`. It is evidence for a later independently validated
M10.5-01 gate; it does not change AIDL language semantics, Production
Normalization admission, Canonical IR meaning, runtime behavior, public support,
or Python's authority.

## Machine-readable authority

`spec/m10-5-parity-manifest.json` defines the bounded parity inventory and
differential contract. `tools/m10_5_python_parity_baseline.py` validates the
manifest and emits deterministic generated parity evidence. The generated
fingerprint content-binds:

- frozen `spec/language-surface-v1.json` revision 4;
- `spec/ir.schema.json`;
- `spec/profile-registry.json`;
- the integrated M10.2 classification;
- the integrated M10.3 shared disposition and closure certification;
- every inventoried Python compiler, CLI/query, fixture/compatibility,
  reference-app, IntelliJ-integration and CI evidence file; and
- the differential comparison contract and baseline base-commit identity.

No semantic allowlist exists. The only declared transport normalization is
repository-relative path rendering plus canonical JSON object-key ordering.

## Exact runner input identity

Every differential run has exactly three inputs: `source`, `config`, and
`profile`. Each is identified by a SHA-256 digest. Missing keys, extra keys, or
different digests fail closed before semantic comparison. This prevents a
Python/Kotlin comparison from silently using different source, configuration or
profile inputs.

## Observable comparison

The structured result contract compares accepted/rejected classification,
diagnostics, Canonical IR, stable identities, ordering, source locations, and
exit behavior. A mismatch is emitted as a structured row naming the semantic
dimension and both values. The harness does not suppress known differences with
allowlists.

`python3 tools/m10_5_python_parity_baseline.py evidence` emits the deterministic
baseline evidence JSON and semantic fingerprint for the current checkout.

## Negative evidence

`tools/test_m10_5_python_parity_baseline.py` proves fail-closed behavior for:

- removal, addition, or substitution of the required runner inputs;
- missing or extra source/config/profile identities;
- source/config/profile identity drift between implementations;
- `spec/ir.schema.json` drift;
- `spec/profile-registry.json` drift;
- semantic fingerprint drift; and
- semantic result mismatches with structured reporting.

M10.5-02 and Kotlin semantic implementation remain blocked until this exact PR
head is independently validated and integrated. Python remains the
reference/conformance implementation throughout this gate.

# M10.5-01 post-G1 current-main Python parity evidence

M10.5-01 was refreshed after the completed Core authority transition and the integrated post-G1 reconciliation. The accepted Python reference/conformance baseline was derived from exact `main@f471fd9c1ee808ff9557d4a9f6bdf8b092d9c2c5`, independently validated at exact PR #94 head `9228f94302c1fbbc6cd5fc0b5fc7af9231071d76`, and integrated on `main` as `fcfc3fc92e6577270dbf89be22c4ddfac5c187a9`. PR #77 remains already-merged historical/provisional parity evidence at `1574963eed95a2f80c1cdc47f48a3eaa39df4a4b`; it is not a pending integration target and did not satisfy the post-G1 Gate-01 refresh by itself.

This package is accepted M10.5-01 evidence. It does not change AIDL language semantics, Production Normalization admission, Canonical IR meaning, runtime behavior, public support, or Python's reference/conformance role. M10.5-02 and later Kotlin semantic work remain blocked until the focused durable-state correction that records this completed Gate 01 receives fresh independent validation and integration.

## Machine-readable authority boundary

`spec/m10-5-parity-manifest.json` defines the bounded parity inventory and differential contract. `tools/m10_5_python_parity_baseline.py` validates the manifest and emits deterministic generated parity evidence. The parity manifest is explicitly non-normative: normative Core/Core-authored modules remain the sole permanent semantic authority.

The generated fingerprint content-binds:

- exact accepted baseline base `main@f471fd9c1ee808ff9557d4a9f6bdf8b092d9c2c5`;
- normative `spec/core.aidl`;
- Core-authored compatibility authority contract `spec/core.authority.aidl`;
- exact Core-authored revision-4 compatibility binding `spec/core.compatibility.aidl`;
- frozen `spec/language-surface-v1.json` revision 4 only as Core-authorized compatibility/conformance evidence;
- `spec/ir.schema.json`;
- `spec/profile-registry.json`;
- the integrated M10.2 classification;
- the integrated M10.3 shared disposition and closure certification;
- current Core-derived/conformance evidence, including the derived Core registry and Core authority/bootstrap/semantic regressions;
- every inventoried Python compiler, CLI/query, fixture/compatibility, reference-app, IntelliJ-integration and CI evidence file; and
- the differential comparison contract.

Drift in Core source, the Core-authored compatibility contract, or the exact compatibility binding changes the fingerprint and therefore fails closed against the accepted baseline. The manifest also rejects any attempt to relabel revision 4 as permanent semantic authority.

No semantic allowlist exists. The only declared transport normalization is repository-relative path rendering plus canonical JSON object-key ordering.

## Exact runner input identity

Every differential run has exactly three inputs: `source`, `config`, and `profile`. Each is identified by a SHA-256 digest. Missing keys, extra keys, or different digests fail closed before semantic comparison. This prevents a Python/Kotlin comparison from silently using different source, configuration or profile inputs.

## Observable comparison

The structured result contract compares accepted/rejected classification, diagnostics, Canonical IR, stable identities, ordering, source locations, and exit behavior. A mismatch is emitted as a structured row naming the semantic dimension and both values. The harness does not suppress known differences with allowlists.

`python3 tools/m10_5_python_parity_baseline.py evidence` emits the deterministic accepted evidence JSON and semantic fingerprint for the current checkout.

## Negative evidence

`tools/test_m10_5_python_parity_baseline.py` proves fail-closed behavior for:

- stale pre-G1/post-M10.3 baseline commit identity;
- semantic-authority role drift that would promote revision 4;
- drift in `spec/core.aidl`;
- drift in `spec/core.authority.aidl`;
- drift in `spec/core.compatibility.aidl`;
- removal, addition, or substitution of the required runner inputs;
- missing or extra source/config/profile identities;
- source/config/profile identity drift between implementations;
- `spec/ir.schema.json` drift;
- `spec/profile-registry.json` drift;
- semantic fingerprint drift; and
- semantic result mismatches with structured reporting.

The historical PR #77 evidence remains useful provenance but is not reused as the post-G1 acceptance target. Gate 01 is complete through independently validated and integrated PR #94. The next semantic roadmap step is M10.5-02, but it remains blocked until the separate durable-state reconciliation recording this completion is independently validated and integrated.

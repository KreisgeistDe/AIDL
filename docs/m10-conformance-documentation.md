# M10-06 Generated Conformance Documentation

M10-06 makes the repository's public support tables derived outputs rather than independent support claims.

## Authorities

`spec/conformance-manifest.json` remains the authority for repository support surfaces. `spec/core-conformance.json` remains the authority for Core declaration/rule layer status, and `spec/core-fixture-conformance.json` must contain exactly the Core Supported feature set derived from Parse/Resolve/Validate/IR status.

`tools/conformance_docs.py` renders two checked-in Markdown blocks from those contracts:

- the support-surface table in `SUPPORT.md` from every manifest surface ID, kind, status, and canonical `supportStatement`;
- the Core Supported coverage table in `docs/12-coverage-and-limits.md` from the exact Core Supported feature IDs and their Parse/Resolve/Validate/IR states.

The generated blocks are bounded by explicit `BEGIN GENERATED` / `END GENERATED` markers. Manual edits inside those blocks are stale by definition.

## Commands

```bash
python3 -m tools.conformance_docs check
python3 -m tools.conformance_docs write
python3 -m unittest tools/test_conformance_docs.py tools/test_conformance_manifest.py tools/test_core_conformance.py
```

Use `write` only after intentionally changing a versioned conformance contract. `check` is read-only and fails if either status page differs byte-for-byte from the deterministic renderer. The focused regression suite also rejects missing markers, Core fixture/support-set drift, and non-deterministic manifest-to-table projection.

This work changes documentation derivation only. It does not promote any manifest surface, Core row, generator/runtime layer, profile, language semantic, or support promise.

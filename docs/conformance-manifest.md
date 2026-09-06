# M10 conformance contracts

`spec/conformance-manifest.json` remains the versioned, machine-readable authority for repository-level support surfaces. Its schema is `spec/conformance-manifest.schema.json` (schema version 1).

M10-02 adds the companion `spec/core-conformance.json` plus `spec/core-conformance.schema.json` (schema version 1). This second machine-readable contract is the exhaustive tracking matrix for the current Core Supported declaration/rule inventory derived from `docs/aidl-core-subset.md`. It does not add or change language semantics.

## Surface identifiers

Repository-wide surfaces retain stable IDs such as `profile.core`, `contract.canonical-ir`, `tooling.cli`, and `runtime.m4-petstore`. Profile IDs remain mechanically tied to `spec/profile-registry.json`, and cross-surface dependencies continue to use those IDs.

## Core identifiers and layers

The Core matrix uses stable IDs with two namespaces:

- `decl.*` for each declaration form currently inventoried from the Core Supported contract;
- `rule.*` for each semantic rule currently inventoried from that contract.

Every row contains exactly the six layers required by the Core contract: `parse`, `resolve`, `validate`, `ir`, `generate`, and `ide`. The matrix currently contains 17 declaration rows and 18 semantic-rule rows.

M10-02 is a tracking/certification change. A row can legitimately expose incomplete implementation. It must not promote later M10 work by inventing missing type checking, generator support, or IDE support.

## Layer status vocabulary

The Core matrix permits exactly:

- `not-applicable` — the layer is not part of that declaration/rule obligation and cites the normative contract;
- `missing` — the obligation exists but no current implementation evidence supports it;
- `partial` — current evidence covers only a bounded subset;
- `implemented` — current executable or machine-readable repository evidence supports the claimed layer.

Documentation-only evidence cannot promote a layer to `implemented`.

## Evidence catalog

`core-conformance.json` centralizes repository-relative evidence in `evidenceCatalog`. Per-layer rows reference stable evidence-set IDs instead of repeating paths. The validator rejects unknown evidence IDs, missing/escaping paths, empty evidence resolution, and implemented statuses backed only by documentation.

The current evidence sets point to compiler/parser sources, compiler-project resolution, compiler diagnostics/fixtures, Canonical IR source/schema, M4 generator/Petstore regression evidence, and the compiler-backed IntelliJ validation boundary. A partial status remains partial even when its evidence file is executable; the status describes the bounded claim, not the quality of the file reference.

## Completeness and drift

`tools/conformance_manifest.py` owns both the M10-01 surface validation and M10-02 Core-matrix validation. It fixes the six-layer vocabulary and the current Core declaration/rule inventory, rejects duplicate/unknown/missing rows, and requires deterministic stable-ID ordering. `SUPPORT.md` also carries a checked Core-matrix count marker so public support documentation cannot silently forget the matrix.

This M10-02 inventory is a machine projection of the accepted Core Supported contract. Changing the normative Core surface requires deliberately changing the inventory, matrix, evidence, tests, and documentation together; parser acceptance alone is not enough to promote support.

## Validation

Run:

```bash
python3 -m tools.conformance_manifest validate
python3 -m unittest tools/test_conformance_manifest.py tools/test_core_conformance.py
```

The focused Core regressions cover unknown layers/statuses/feature IDs, duplicate rows, unknown or missing evidence, deterministic inventory drift, and impermissible promotion from documentation-only evidence. M9-01 discovers the new `tools/test_core_conformance.py` module automatically in the generic Python CI gate.

## Scope boundaries

M10-02 changes only conformance metadata, validation, tests, and documentation. It does not change parser behavior, compiler semantics, Canonical IR shape, generator output, or IntelliJ semantics.

Later M10 items still own complete compiler type checking, explicit rejection of unsupported/unmaterialized constructs, exhaustive fixture coverage, and generated coverage tables. Native `main` branch protection remains open under M9-06 and continues to be represented by `repository.main-protection` with status `blocked`.

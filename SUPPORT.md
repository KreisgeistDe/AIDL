# AIDL Support and Stability Status

AIDL is a pre-1.0 specification and reference implementation. Support claims are intentionally narrower than the full language specification. `spec/conformance-manifest.json` is the machine-readable authority for repository support surfaces; current source, executable tests/CI, machine-readable contracts, and `TODO.md` provide its evidence.

M10-02 adds `spec/core-conformance.json` as the machine-readable Core declaration/rule layer matrix governed by `tools/conformance_manifest.py`. It tracks every currently inventoried Core declaration and semantic rule across Parse, Resolve, Validate, IR, Generate, and IDE without promoting partial or missing implementation evidence.

Core conformance matrix: 17 declarations, 18 semantic rules, 6 layers.

## Support matrix

The table below is generated from `spec/conformance-manifest.json`. Run `python3 -m tools.conformance_docs write` after an intentional manifest change; `python3 -m tools.conformance_docs check` and the Python regression suite reject manual or stale edits.

<!-- BEGIN GENERATED: conformance-surface-coverage -->
| Manifest ID | Kind | Status | Canonical support statement |
|---|---|---|---|
| `contract.canonical-ir` | contract | implemented | Canonical IR is implemented at irVersion 0.3.0 with a closed schema and deterministic serialization for the implemented compiler subset. |
| `profile.cloud` | profile | partial | Cloud profile support is partial: selected declarations and semantics are compiler-visible, but complete provider adapters and runtime coverage are not implemented. |
| `profile.core` | profile | partial | Core support is partial at conformance level: parser, compiler-owned resolution and validation, diagnostics, and Canonical IR exist for the documented subset, while M10 layer-completeness certification remains open. |
| `profile.distributed` | profile | partial | Distributed profile support is partial: selected compiler and fixture semantics are implemented, but a general multi-service runtime remains future work. |
| `profile.media` | profile | partial | Media profile support is partial: selected syntax and compiler/fixture evidence exist, but upload, transcoding, delivery, and provider runtime support are not complete. |
| `profile.offline` | profile | partial | Offline profile support is partial: selected sync/conflict semantics are represented in compiler fixtures, but the complete offline multi-writer runtime is not implemented. |
| `profile.realtime` | profile | specified | Realtime is currently a specified profile; no production channel runtime support is claimed. |
| `profile.web` | profile | specified | Web is currently a specified profile; complete compiler, generator, and runtime conformance is not claimed. |
| `release.bundle` | release | implemented | The reproducible release bundle is implemented as a dry run with manifest, SHA-256 checksums, tracked contracts, and publication disabled. |
| `repository.main-protection` | repository | blocked | Native main branch protection remains blocked/open and must not be described as enforced. |
| `runtime.m4-petstore` | runtime | implemented | The bounded M4 TypeScript/Fastify/PostgreSQL Petstore vertical slice is implemented and tested; it is not a general runtime for every profile. |
| `tooling.cli` | tooling | implemented | The compiler-owned aidl CLI is implemented and installable for Python 3.12 with its registered command surface and versioned JSON output contracts. |
| `tooling.intellij` | tooling | partial | IntelliJ support is partial at conformance level: documented compiler-backed diagnostics, fixes, navigation, rename, completion, and documentation paths exist, but full-profile editor conformance is not claimed. |
| `tooling.lsp` | tooling | experimental | The LSP surface is experimental: only the saved-file stdio proof of concept is claimed, not production unsaved-buffer support. |
<!-- END GENERATED: conformance-surface-coverage -->

The surface statuses, dependencies, summaries, and evidence paths live in `spec/conformance-manifest.json`. The Core row/layer statuses and evidence references live in `spec/core-conformance.json`. Neither document may be used to infer implementation beyond its explicit status.

## Core layer semantics

The Core matrix uses exactly `parse`, `resolve`, `validate`, `ir`, `generate`, and `ide` and exactly four layer states: `not-applicable`, `missing`, `partial`, and `implemented`. `implemented` requires executable or machine-readable repository evidence; documentation-only evidence cannot promote a layer to implemented. `partial` records real evidence with known gaps, while `missing` is an explicit gap rather than an inferred implementation.

M10-02 is tracking work only. It does not implement missing type checking, generator behavior, or IDE behavior. Those remain later M10 items. M9-06 native `main` branch protection also remains open.

## CLI and version domains

The following versions are separate contracts and must not be conflated:

- distribution/package baseline: `aidl-toolchain` `0.0.0`;
- Canonical IR: `0.3.0`;
- current CLI JSON schema artifact: `7.0.0`;
- profile registry: `0.3.0`, with independent profile majors;
- conformance surface manifest schema: `1`;
- Core conformance matrix schema: `1`.

A version number in one domain does not imply equal maturity or compatibility guarantees in another.

## What "supported" means here

A surface is considered implemented only for the bounded scope described by its manifest entry and only when the required path exists in current code with executable or machine-readable evidence. Documentation, grammar, schema representation, registry entries, or examples alone do not establish full end-to-end support.

For the detailed capability boundary, see `docs/12-coverage-and-limits.md`. For the conformance contracts see `docs/conformance-manifest.md`; for package installation see `docs/m9-cli-packaging.md`; for release construction see `docs/m9-release-workflow.md`; for artifact integrity/provenance claims see `docs/artifact-provenance.md`.

## Compatibility and change expectations

Before 1.0, unsupported or explicitly experimental surfaces may change without a production-stability promise. Versioned machine contracts and compatibility rules should be changed deliberately and with matching tests. Contributors should not infer stability from a successful parse, an IR field, a manifest entry, or a profile name alone.

## Support requests

Use normal repository issues for non-sensitive bug reports and support questions when an issue tracker is available. Include the relevant commit/package version, command, minimized input, expected behavior, actual behavior, and validation output. Security-sensitive reports must follow `SECURITY.md` instead of public issue discussion.

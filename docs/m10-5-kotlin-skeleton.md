# M10.5-02 Kotlin Multiplatform compiler skeleton

M10.5-02 introduces only the first non-normative Kotlin compiler-core skeleton. Python remains the reference and conformance implementation. This package does not parse AIDL, construct Canonical IR, emit compiler diagnostics, change Production Normalization admission, alter runtime behavior, or start M10.5-03 semantic migration.

## Boundary

`compiler/kotlin` is an isolated Kotlin Multiplatform build. Its `commonMain` source set contains only parity-contract scaffolding and deterministic transport utilities. `jvmMain` and `linuxX64Main` are thin adapters that both consume that common contract. Filesystem, process, IDE, and other platform integrations are intentionally absent from common code.

The skeleton inherits the integrated M10.5-01 contract without modification:

- runner inputs are exactly `source`, `config`, and `profile`;
- each input identity must be an exact lower-case `sha256:` identity for those three keys and no others;
- semantic allowlists remain empty and forbidden;
- the contract records the same six normative fingerprint bindings: `spec/language-surface-v1.json`, `spec/ir.schema.json`, `spec/profile-registry.json`, `spec/m10-2-language-surface-classification.json`, `spec/m10-3-shared-disposition.json`, and `spec/m10-3-closure-certification.json`;
- Kotlin remains non-normative and cannot independently broaden or reinterpret those authorities.

## Determinism and coverage

The common utility emits JSON objects in sorted-key order with deterministic escaping. Focused Kotlin tests exercise the exact input-key set, SHA-256 identity rejection paths, empty semantic allowlist, deterministic rendering, and JVM delegation. A repository-side Python structure regression checks the KMP target split, exact inherited contract values, and absence of JVM/Native platform imports from common code.

Kover enforces at least 95% line coverage and 95% branch coverage for the JVM-executed common/JVM skeleton. CI also links the `linuxX64` release executable to prove that the Native adapter consumes the same common source set.

## Status

This is a candidate M10.5-02 implementation only. M10.5-02 is not complete until this exact PR head is independently validated and integrated. M10.5-03 and later semantic migration remain blocked.

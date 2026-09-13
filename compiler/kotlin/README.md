# Kotlin compiler migration (M10.5)

This directory contains the non-normative Kotlin Multiplatform compiler work for M10.5. Python remains the reference/conformance implementation. Nothing here changes AIDL language semantics, Production Normalization admission, Canonical IR meaning, runtime behavior, reference-app behavior, or public support.

The build deliberately reuses the repository's existing Gradle wrapper at `plugins/intellij/gradlew` instead of introducing a second wrapper binary. From the repository root:

```bash
plugins/intellij/gradlew -p compiler/kotlin --no-daemon check koverVerify koverXmlReport linkReleaseExecutableLinuxX64
```

## M10.5-02 platform boundary

Gate 02 is represented by one Kotlin Multiplatform module with three intentional boundaries:

- `commonMain` owns platform-neutral compiler contracts, deterministic parity serialization, and the already integrated bounded front-end slices. `CommonCompilerBoundary` is the adapter-facing entry point for Gate-02 infrastructure.
- `jvmMain` is a thin host adapter. `JvmCompilerAdapter` delegates to `CommonCompilerBoundary`; JVM filesystem, process, IDE/LSP protocol, and other host integration must remain outside common semantic packages.
- `linuxX64Main` is a thin Kotlin/Native CLI adapter. Its executable delegates to the same `CommonCompilerBoundary`; command-line/process/distribution concerns are Native-only and must not duplicate parser, resolver, type, validation, diagnostic, IR, or compatibility semantics.

The only unavoidable platform-specific boundary in this gate is host integration: JVM consumers need JVM entry points, while the Native executable needs a platform entry point and later distribution/process integration. Both consume the same common contracts and neither owns semantic implementation.

The integrated M10.5-01 contract is inherited exactly: runner inputs are `source`, `config`, and `profile`; their identities are exact SHA-256 values; Core authority inputs are separately bound as `spec/core.aidl`, `spec/core.authority.aidl`, and `spec/core.compatibility.aidl`; the inherited six parity bindings remain unchanged; semantic allowlists are forbidden; Python remains the reference/conformance implementation.

`DeterministicJson` and `CommonCompilerBoundary.deterministicContractSnapshot()` provide structure-stable Gate-02 evidence shared by JVM and Native adapters. Kover verification enforces at least 95% line and branch coverage for JVM-executed common/JVM code, and the Native target must compile and link from the same common source set. The common tests exercise deterministic serialization, exact authority inventories, fail-closed runner identity validation, and the shared adapter-facing boundary.

## M10.5-03 bounded front-end slices

`AidlSourceProjector` implements only deterministic lexical/source projection for module/import headers and named `enum`, `value`, and `entity` declaration boundaries. Declaration bodies are retained as lexical tokens so canonical and legacy spellings can be compared without moving resolution, typing, validation, diagnostics, Canonical IR, Production Normalization, or runtime semantics into Kotlin. Any top-level declaration kind outside this explicit slice fails closed.

`ProjectNameResolver` is the next bounded slice over that projection. It mirrors only the Python `compiler_project`/`compiler_resolution` behavior needed for module-qualified declaration FQNs, explicit and wildcard exported imports, local-module lookup, imported short-name lookup, direct qualified lookup, stable project order, duplicate preservation, and resolved/unresolved/ambiguous classification. Stable identities combine the Python-derived FQN with the deterministic source ID and declaration ordinal so duplicate FQNs remain distinguishable without changing language meaning.

Shared fixtures under `parity/` are executed by Kotlin and independently pinned to the Python parser/project/resolution oracle by `tools/test_m10_5_kotlin_parser_projection.py` and `tools/test_m10_5_kotlin_name_resolution.py`. This remains historical/bounded evidence only for the covered surface; this Gate-02 package does not expand those slices and does not claim M10.5-03 Gate 03 completion.

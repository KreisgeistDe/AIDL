# Kotlin compiler migration (M10.5)

This directory contains the non-normative Kotlin Multiplatform compiler work for M10.5. Python remains the reference/conformance implementation. Nothing here changes AIDL language semantics, Production Normalization admission, Canonical IR meaning, runtime behavior, reference-app behavior, or public support.

The build deliberately reuses the repository's existing Gradle wrapper at `plugins/intellij/gradlew` instead of introducing a second wrapper binary. From the repository root:

```bash
plugins/intellij/gradlew -p compiler/kotlin --no-daemon check koverVerify koverXmlReport linkReleaseExecutableLinuxX64
```

Source-set boundaries are intentional:

- `commonMain` owns platform-neutral parity contracts plus the bounded source-projection and name-resolution slices.
- `jvmMain` remains a thin adapter; JVM-only fixture execution may exercise common code but owns no compiler semantics.
- `linuxX64Main` remains a thin Kotlin/Native CLI adapter and owns no compiler semantics.

The integrated M10.5-01 contract is inherited exactly: runner inputs are `source`, `config`, and `profile`; their identities are exact SHA-256 values; the semantic fingerprint remains bound to the six current normative authorities; semantic allowlists are forbidden.

## M10.5-03 bounded front-end slices

`AidlSourceProjector` implements only deterministic lexical/source projection for module/import headers and named `enum`, `value`, and `entity` declaration boundaries. Declaration bodies are retained as lexical tokens so canonical and legacy spellings can be compared without moving resolution, typing, validation, diagnostics, Canonical IR, Production Normalization, or runtime semantics into Kotlin. Any top-level declaration kind outside this explicit slice fails closed.

`ProjectNameResolver` is the next bounded slice over that projection. It mirrors only the Python `compiler_project`/`compiler_resolution` behavior needed for module-qualified declaration FQNs, explicit and wildcard exported imports, local-module lookup, imported short-name lookup, direct qualified lookup, stable project order, duplicate preservation, and resolved/unresolved/ambiguous classification. Stable identities combine the Python-derived FQN with the deterministic source ID and declaration ordinal so duplicate FQNs remain distinguishable without changing language meaning.

Shared fixtures under `parity/` are executed by Kotlin and independently pinned to the Python parser/project/resolution oracle by `tools/test_m10_5_kotlin_parser_projection.py` and `tools/test_m10_5_kotlin_name_resolution.py`. This remains evidence only for the bounded covered surface; it is not a claim that M10.5-03 Gate 03 or the complete front end is finished.

Kover verification continues to enforce at least 95% line and branch coverage for JVM-executed common/JVM code, and the Native target must compile and link from the same common source set.

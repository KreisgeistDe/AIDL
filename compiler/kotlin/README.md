# Kotlin compiler migration (M10.5)

This directory contains the non-normative Kotlin Multiplatform compiler work for M10.5. Python remains the reference/conformance implementation. Nothing here changes AIDL language semantics, Production Normalization admission, Canonical IR meaning, runtime behavior, reference-app behavior, or public support.

The build deliberately reuses the repository's existing Gradle wrapper at `plugins/intellij/gradlew` instead of introducing a second wrapper binary. From the repository root:

```bash
plugins/intellij/gradlew -p compiler/kotlin --no-daemon check koverVerify koverXmlReport linkReleaseExecutableLinuxX64
```

Source-set boundaries are intentional:

- `commonMain` owns platform-neutral parity contracts and the bounded source-projection implementation.
- `jvmMain` remains a thin adapter; JVM-only fixture execution may exercise common code but owns no parser semantics.
- `linuxX64Main` remains a thin Kotlin/Native CLI adapter and owns no compiler semantics.

The integrated M10.5-01 contract is inherited exactly: runner inputs are `source`, `config`, and `profile`; their identities are exact SHA-256 values; the semantic fingerprint remains bound to the six current normative authorities; semantic allowlists are forbidden.

## M10.5-03 first bounded front-end slice

`AidlSourceProjector` implements only deterministic lexical/source projection for module/import headers and named `enum`, `value`, and `entity` declaration boundaries. Declaration bodies are retained as lexical tokens so canonical and legacy spellings can be compared without moving resolution, typing, validation, diagnostics, Canonical IR, Production Normalization, or runtime semantics into Kotlin. Any top-level declaration kind outside this explicit slice fails closed.

Shared fixtures under `parity/` are executed by Kotlin and independently pinned to the Python `tools.aidl_parser` oracle by `tools/test_m10_5_kotlin_parser_projection.py`. The fixtures cover the canonical data-declaration spelling and retained legacy entity-field spelling. This is evidence for only this bounded source-projection subset; it is not a claim that M10.5-03 Gate 03 or the complete parser surface is finished.

Kover verification continues to enforce at least 95% line and branch coverage for JVM-executed common/JVM code, and the Native target must compile and link from the same common source set.

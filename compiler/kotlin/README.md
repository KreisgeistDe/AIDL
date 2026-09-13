# Kotlin compiler skeleton (M10.5-02)

This directory is the non-normative Kotlin Multiplatform compiler skeleton for M10.5-02. Python remains the reference/conformance implementation. Nothing here changes AIDL language semantics, Production Normalization admission, Canonical IR meaning, runtime behavior, reference-app behavior, or public support.

The build deliberately reuses the repository's existing Gradle wrapper at `plugins/intellij/gradlew` instead of introducing a second wrapper binary. From the repository root:

```bash
plugins/intellij/gradlew -p compiler/kotlin --no-daemon check koverVerify koverXmlReport linkReleaseExecutableLinuxX64
```

Source-set boundaries are intentional:

- `commonMain` owns only platform-neutral contract scaffolding and deterministic transport utilities.
- `jvmMain` is a thin adapter that exposes the same common contract snapshot for future JVM consumers.
- `linuxX64Main` is a thin Kotlin/Native CLI adapter that emits the same common contract snapshot and owns no compiler semantics.

The integrated M10.5-01 contract is inherited exactly: runner inputs are `source`, `config`, and `profile`; their identities are exact SHA-256 values; the semantic fingerprint remains bound to the six current normative authorities; semantic allowlists are forbidden. The Kotlin skeleton validates only the contract boundary. It does not parse AIDL, construct Canonical IR, emit diagnostics, or claim differential parity.

Kover verification enforces at least 95% line and branch coverage for the JVM-executed common/JVM skeleton. The Native target must compile and link from the same common source set. M10.5-03 remains blocked until this exact skeleton is independently validated and integrated.

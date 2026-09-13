# M10.5-02 Kotlin Multiplatform compiler skeleton

## Status

This package certifies the Gate-02 Kotlin Multiplatform skeleton without changing AIDL semantics or moving conformance authority away from Python. The package is an implementation candidate until independently validated and integrated.

## Platform-neutral boundary

`compiler/kotlin/src/commonMain` is the only home for compiler-owned Kotlin contracts and deterministic parity infrastructure. `CommonCompilerBoundary` is the adapter-facing Gate-02 entry point. Both `JvmCompilerAdapter` and the Linux/Native executable delegate to that object; neither adapter implements parser, resolver, type, validation, diagnostic, Canonical-IR, compatibility, or other semantic behavior.

Platform-specific code is limited to unavoidable host integration:

- JVM entry points for JVM-hosted consumers and later IDE/LSP integration;
- Kotlin/Native executable/process/distribution entry points;
- future filesystem, transport, process, or protocol integration, which must stay outside common semantic packages.

The pre-existing `SourceProjection`, `NameResolution`, and `TypeConstruction` code remains bounded M10.5-03 evidence. Gate 02 does not reinterpret or expand those slices and does not claim Gate 03 completion.

## Inherited Gate-01 contract

Python remains the reference/conformance implementation. Kotlin inherits the accepted M10.5-01 contract exactly:

- runner inputs are exactly `source`, `config`, and `profile` with SHA-256 identity;
- Core authority bindings are separately recorded as `spec/core.aidl`, `spec/core.authority.aidl`, and `spec/core.compatibility.aidl`;
- the six inherited parity bindings remain unchanged;
- semantic allowlists remain empty;
- revision 4 remains Core-authorized compatibility/conformance evidence only.

`ParityContract` and `CommonCompilerBoundary.deterministicContractSnapshot()` expose deterministic, structure-stable contract evidence for both platform adapters.

## Coverage and executable evidence

`compiler/kotlin/build.gradle.kts` enforces Kover minimums of 95% line coverage and 95% branch coverage for JVM-executed common/JVM code. Common tests cover deterministic serialization, exact runner-input identity, malformed/missing/extra identity rejection, exact Core/parity binding inventories, and deterministic adapter-facing snapshots. Existing focused tests continue to cover the bounded front-end slices without broadening their semantics.

The Gate-02 validation command is:

```bash
plugins/intellij/gradlew -p compiler/kotlin --no-daemon check koverVerify koverXmlReport linkReleaseExecutableLinuxX64
```

Acceptance requires the JVM/common test suite and Kover verification to pass and the Native executable to link from the same common source set. Repository CI remains the authoritative exact-head execution gate.

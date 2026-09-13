# M10.5-02 Kotlin Multiplatform compiler skeleton

## Status

Gate 02 is complete. PR #97 exact independently validated head `dfb3af756f2c726f925ee16bddecebe004e5c781` was squash-integrated on main as `5ca01218246982e4b21701254bf3f1844b103014` with sole parent `11fd92d991cf2ff9f5354589dbfd0c0397908621` and the exact seven-path Gate-02 scope. Resulting-main push Validation #409 run `34760402346` and Kotlin Compiler Skeleton #66 run `34760402339` completed successfully. This completion does not change AIDL semantics or move conformance authority away from Python, and it does not complete Gate 03.

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

The accepted exact-head evidence passed the JVM/common test suite and configured Kover gates and linked the Native executable from the same common source set. The workflow did not publish raw numeric coverage percentages, so Gate-02 acceptance records only the configured-and-passed minimum thresholds rather than inventing figures.

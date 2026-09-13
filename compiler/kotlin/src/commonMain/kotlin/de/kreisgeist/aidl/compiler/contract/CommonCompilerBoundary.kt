package de.kreisgeist.aidl.compiler.contract

/**
 * Platform-neutral Gate-02 boundary consumed by both JVM and Native adapters.
 *
 * This object deliberately exposes only deterministic migration/parity contract data.
 * It owns no parser, resolver, type, validation, diagnostic, Canonical-IR, filesystem,
 * process, transport, or protocol semantics.
 */
object CommonCompilerBoundary {
    fun deterministicContractSnapshot(): String =
        DeterministicJson.objectOf(ParityContract.contractSnapshot())
}

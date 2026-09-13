package de.kreisgeist.aidl.compiler.contract

object ParityContract {
    const val schemaVersion = "aidl.m10.5-python-parity-baseline/v1"
    const val referenceImplementation = "python"

    private val sha256Identity = Regex("^sha256:[0-9a-f]{64}$")

    val runnerInputs: List<String> = listOf("source", "config", "profile")

    val coreAuthorityBindings: List<String> = listOf(
        "spec/core.aidl",
        "spec/core.authority.aidl",
        "spec/core.compatibility.aidl",
    )

    val normativeBindings: List<String> = listOf(
        "spec/language-surface-v1.json",
        "spec/ir.schema.json",
        "spec/profile-registry.json",
        "spec/m10-2-language-surface-classification.json",
        "spec/m10-3-shared-disposition.json",
        "spec/m10-3-closure-certification.json",
    )

    val semanticAllowlists: List<String> = emptyList()

    fun validateInputIdentity(identity: Map<String, String>): Map<String, String> {
        require(identity.keys == runnerInputs.toSet()) {
            "runner input identity must contain exactly source, config, profile"
        }
        return runnerInputs.associateWith { key ->
            val value = identity.getValue(key)
            require(sha256Identity.matches(value)) { "invalid sha256 identity for runner input $key" }
            value
        }
    }

    fun contractSnapshot(): Map<String, String> = mapOf(
        "reference_implementation" to referenceImplementation,
        "runner_inputs" to runnerInputs.joinToString(","),
        "semantic_allowlists" to semanticAllowlists.size.toString(),
        "core_authority_bindings" to coreAuthorityBindings.joinToString(","),
        "normative_bindings" to normativeBindings.joinToString(","),
    )
}

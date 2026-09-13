package de.kreisgeist.aidl.compiler.contract

object ParityContract {
    const val schemaVersion = "aidl.m10.5-python-parity-baseline/v1"
    const val referenceImplementation = "python"

    val runnerInputs: List<String> = listOf("source", "config", "profile")

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
            val value = requireNotNull(identity[key])
            require(isSha256Identity(value)) { "invalid sha256 identity for runner input $key" }
            value
        }
    }

    fun contractSnapshot(): Map<String, String> = mapOf(
        "reference_implementation" to referenceImplementation,
        "runner_inputs" to runnerInputs.joinToString(","),
        "semantic_allowlists" to semanticAllowlists.size.toString(),
        "normative_bindings" to normativeBindings.joinToString(","),
    )

    private fun isSha256Identity(value: String): Boolean =
        value.length == 71 &&
            value.startsWith("sha256:") &&
            value.drop(7).all { it in '0'..'9' || it in 'a'..'f' }
}

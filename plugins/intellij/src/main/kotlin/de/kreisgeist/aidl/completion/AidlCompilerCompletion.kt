package de.kreisgeist.aidl.completion

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import de.kreisgeist.aidl.diagnostics.DefaultAidlProcessRunner
import java.nio.file.Files
import java.nio.file.Path

data class AidlCompletionCandidate(
    val insertText: String,
    val displayText: String,
    val fullyQualifiedName: String,
    val kind: String,
    val origin: String,
)

sealed interface AidlCompletionResult {
    data class Resolved(
        val prefix: String,
        val qualifier: String?,
        val candidates: List<AidlCompletionCandidate>,
    ) : AidlCompletionResult

    data object NoCandidates : AidlCompletionResult
    data class Failure(val kind: AidlCompletionFailureKind, val message: String) : AidlCompletionResult
}

enum class AidlCompletionFailureKind {
    PROCESS,
    COMPILER,
    JSON,
}

class AidlCompilerCompletionAdapter(
    private val processRunner: AidlProcessRunner = DefaultAidlProcessRunner(),
    private val executable: List<String> = listOf("aidl"),
) {
    fun complete(projectPath: Path, sourcePath: Path, offset: Int): AidlCompletionResult {
        val normalizedProject = projectPath.toAbsolutePath().normalize()
        val normalizedSource = sourcePath.toAbsolutePath().normalize()
        val workingDirectory = when {
            Files.isDirectory(normalizedProject) -> normalizedProject
            normalizedProject.parent != null -> normalizedProject.parent
            else -> Path.of(".").toAbsolutePath().normalize()
        }
        val command = executable + listOf(
            "complete",
            normalizedProject.toString(),
            "--file",
            normalizedSource.toString(),
            "--offset",
            offset.toString(),
            "--format",
            "json",
        )
        val output = try {
            processRunner.run(command, workingDirectory)
        } catch (exception: Exception) {
            return AidlCompletionResult.Failure(
                AidlCompletionFailureKind.PROCESS,
                "failed to execute AIDL compiler: ${exception.message ?: exception::class.simpleName}",
            )
        }
        if (output.exitCode == 70) {
            return AidlCompletionResult.Failure(
                AidlCompletionFailureKind.COMPILER,
                "AIDL compiler reported an internal failure",
            )
        }
        if (output.exitCode != 0) {
            return AidlCompletionResult.Failure(
                AidlCompletionFailureKind.PROCESS,
                "AIDL compiler exited with unexpected status ${output.exitCode}",
            )
        }
        return try {
            parseEnvelope(output.stdout)
        } catch (exception: Exception) {
            AidlCompletionResult.Failure(
                AidlCompletionFailureKind.JSON,
                "invalid AIDL compiler completion JSON response: ${exception.message ?: exception::class.simpleName}",
            )
        }
    }

    private fun parseEnvelope(text: String): AidlCompletionResult {
        val root = JsonParser.parseString(text).asObject("root")
        require(root.requiredString("command") == "complete") { "command must be 'complete'" }
        require(root.requiredBoolean("ok")) { "complete response must have ok=true" }
        val result = root.requiredObject("result")
        return when (result.requiredString("status")) {
            "invalid", "unresolved", "ambiguous" -> AidlCompletionResult.NoCandidates
            "resolved" -> {
                val candidatesElement = result.get("candidates") ?: throw IllegalArgumentException("missing 'candidates'")
                require(candidatesElement.isJsonArray) { "'candidates' must be an array" }
                AidlCompletionResult.Resolved(
                    prefix = result.optionalString("prefix") ?: "",
                    qualifier = result.optionalString("qualifier"),
                    candidates = candidatesElement.asJsonArray.map { element ->
                        val candidate = element.asObject("candidate")
                        AidlCompletionCandidate(
                            insertText = candidate.requiredString("insertText"),
                            displayText = candidate.requiredString("displayText"),
                            fullyQualifiedName = candidate.requiredString("fullyQualifiedName"),
                            kind = candidate.requiredString("kind"),
                            origin = candidate.requiredString("origin"),
                        )
                    },
                )
            }
            else -> throw IllegalArgumentException("unknown completion status")
        }
    }
}

private fun JsonElement.asObject(label: String): JsonObject {
    require(isJsonObject) { "$label must be an object" }
    return asJsonObject
}

private fun JsonObject.requiredObject(name: String): JsonObject =
    (get(name) ?: throw IllegalArgumentException("missing '$name'"))
        .asObject("'$name'")

private fun JsonObject.requiredString(name: String): String {
    val element = get(name) ?: throw IllegalArgumentException("missing '$name'")
    require(element.isJsonPrimitive && element.asJsonPrimitive.isString) { "'$name' must be a string" }
    return element.asString
}

private fun JsonObject.optionalString(name: String): String? {
    val element = get(name) ?: return null
    if (element.isJsonNull) return null
    require(element.isJsonPrimitive && element.asJsonPrimitive.isString) { "'$name' must be a string" }
    return element.asString
}

private fun JsonObject.requiredBoolean(name: String): Boolean {
    val element = get(name) ?: throw IllegalArgumentException("missing '$name'")
    require(element.isJsonPrimitive && element.asJsonPrimitive.isBoolean) { "'$name' must be a boolean" }
    return element.asBoolean
}

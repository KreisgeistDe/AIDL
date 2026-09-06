package de.kreisgeist.aidl.references

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import de.kreisgeist.aidl.diagnostics.DefaultAidlProcessRunner
import java.nio.file.Files
import java.nio.file.Path

data class AidlReferenceTargetLocation(
    val file: String,
    val line: Int,
    val column: Int,
    val offset: Int,
)

data class AidlCompilerReferenceTarget(
    val fullyQualifiedName: String,
    val kind: String,
    val location: AidlReferenceTargetLocation,
)

enum class AidlReferenceFailureKind {
    PROCESS,
    COMPILER,
    JSON,
}

sealed interface AidlReferenceResolutionResult {
    data class Resolved(val target: AidlCompilerReferenceTarget) : AidlReferenceResolutionResult
    data object NoTarget : AidlReferenceResolutionResult
    data class Failure(val kind: AidlReferenceFailureKind, val message: String) : AidlReferenceResolutionResult
}

class AidlCompilerReferenceResolver(
    private val processRunner: AidlProcessRunner = DefaultAidlProcessRunner(),
    private val executable: List<String> = listOf("aidl"),
) {
    fun resolve(projectPath: Path, sourcePath: Path, offset: Int): AidlReferenceResolutionResult {
        val normalizedProject = projectPath.toAbsolutePath().normalize()
        val normalizedSource = sourcePath.toAbsolutePath().normalize()
        val workingDirectory = when {
            Files.isDirectory(normalizedProject) -> normalizedProject
            normalizedProject.parent != null -> normalizedProject.parent
            else -> Path.of(".").toAbsolutePath().normalize()
        }
        val command = executable + listOf(
            "resolve",
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
            return AidlReferenceResolutionResult.Failure(
                AidlReferenceFailureKind.PROCESS,
                "failed to execute AIDL compiler: ${exception.message ?: exception::class.simpleName}",
            )
        }
        if (output.exitCode == 70) {
            return AidlReferenceResolutionResult.Failure(
                AidlReferenceFailureKind.COMPILER,
                "AIDL compiler reported an internal failure",
            )
        }
        if (output.exitCode != 0) {
            return AidlReferenceResolutionResult.Failure(
                AidlReferenceFailureKind.PROCESS,
                "AIDL compiler exited with unexpected status ${output.exitCode}",
            )
        }

        return try {
            parseEnvelope(output.stdout)
        } catch (exception: Exception) {
            AidlReferenceResolutionResult.Failure(
                AidlReferenceFailureKind.JSON,
                "invalid AIDL compiler JSON response: ${exception.message ?: exception::class.simpleName}",
            )
        }
    }

    private fun parseEnvelope(text: String): AidlReferenceResolutionResult {
        val root = JsonParser.parseString(text).asObject("root")
        require(root.requiredString("command") == "resolve") { "command must be 'resolve'" }
        require(root.requiredBoolean("ok")) { "resolve response must have ok=true" }
        val result = root.requiredObject("result")
        return when (result.requiredString("status")) {
            "unresolved", "ambiguous", "invalid" -> AidlReferenceResolutionResult.NoTarget
            "resolved" -> {
                val target = result.requiredObject("target")
                val location = target.requiredObject("location")
                AidlReferenceResolutionResult.Resolved(
                    AidlCompilerReferenceTarget(
                        fullyQualifiedName = target.requiredString("fullyQualifiedName"),
                        kind = target.requiredString("kind"),
                        location = AidlReferenceTargetLocation(
                            file = location.requiredString("file"),
                            line = location.requiredInt("line"),
                            column = location.requiredInt("column"),
                            offset = location.requiredInt("offset"),
                        ),
                    ),
                )
            }
            else -> throw IllegalArgumentException("unknown resolve status")
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

private fun JsonObject.requiredBoolean(name: String): Boolean {
    val element = get(name) ?: throw IllegalArgumentException("missing '$name'")
    require(element.isJsonPrimitive && element.asJsonPrimitive.isBoolean) { "'$name' must be a boolean" }
    return element.asBoolean
}

private fun JsonObject.requiredInt(name: String): Int {
    val element = get(name) ?: throw IllegalArgumentException("missing '$name'" )
    require(element.isJsonPrimitive && element.asJsonPrimitive.isNumber) { "'$name' must be a number" }
    return element.asInt
}

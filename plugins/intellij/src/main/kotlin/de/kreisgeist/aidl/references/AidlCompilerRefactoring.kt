package de.kreisgeist.aidl.references

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import de.kreisgeist.aidl.diagnostics.DefaultAidlProcessRunner
import java.nio.file.Files
import java.nio.file.Path

data class AidlUsageLocation(
    val file: String,
    val line: Int,
    val column: Int,
    val offset: Int,
    val length: Int,
)

sealed interface AidlUsagesResult {
    data class Resolved(
        val target: AidlCompilerReferenceTarget,
        val usages: List<AidlUsageLocation>,
    ) : AidlUsagesResult

    data object NoTarget : AidlUsagesResult
    data class Failure(val kind: AidlRefactoringFailureKind, val message: String) : AidlUsagesResult
}

sealed interface AidlRenameResult {
    data class Applied(
        val newFullyQualifiedName: String,
        val edits: List<AidlUsageLocation>,
    ) : AidlRenameResult

    data class Rejected(val status: String, val message: String?) : AidlRenameResult
    data class Failure(val kind: AidlRefactoringFailureKind, val message: String) : AidlRenameResult
}

enum class AidlRefactoringFailureKind {
    PROCESS,
    COMPILER,
    JSON,
}

class AidlCompilerRefactoringAdapter(
    private val processRunner: AidlProcessRunner = DefaultAidlProcessRunner(),
    private val executable: List<String> = listOf("aidl"),
) {
    fun findUsages(projectPath: Path, sourcePath: Path, offset: Int): AidlUsagesResult {
        val command = commandPrefix(projectPath) + listOf(
            "usages",
            projectPath.toAbsolutePath().normalize().toString(),
            "--file",
            sourcePath.toAbsolutePath().normalize().toString(),
            "--offset",
            offset.toString(),
            "--format",
            "json",
        )
        val output = run(command, projectPath) ?: return AidlUsagesResult.Failure(
            AidlRefactoringFailureKind.PROCESS,
            "failed to execute AIDL compiler",
        )
        if (output.exitCode == 70) {
            return AidlUsagesResult.Failure(AidlRefactoringFailureKind.COMPILER, "AIDL compiler reported an internal failure")
        }
        if (output.exitCode != 0) {
            return AidlUsagesResult.Failure(
                AidlRefactoringFailureKind.PROCESS,
                "AIDL compiler exited with unexpected status ${output.exitCode}",
            )
        }
        return try {
            parseUsages(output.stdout)
        } catch (exception: Exception) {
            AidlUsagesResult.Failure(
                AidlRefactoringFailureKind.JSON,
                "invalid AIDL compiler usages JSON response: ${exception.message ?: exception::class.simpleName}",
            )
        }
    }

    fun rename(projectPath: Path, sourcePath: Path, offset: Int, newName: String): AidlRenameResult {
        val command = commandPrefix(projectPath) + listOf(
            "rename",
            projectPath.toAbsolutePath().normalize().toString(),
            "--file",
            sourcePath.toAbsolutePath().normalize().toString(),
            "--offset",
            offset.toString(),
            "--new-name",
            newName,
            "--apply",
            "--format",
            "json",
        )
        val output = run(command, projectPath) ?: return AidlRenameResult.Failure(
            AidlRefactoringFailureKind.PROCESS,
            "failed to execute AIDL compiler",
        )
        if (output.exitCode == 70) {
            return AidlRenameResult.Failure(AidlRefactoringFailureKind.COMPILER, "AIDL compiler reported an internal failure")
        }
        if (output.exitCode !in setOf(0, 1)) {
            return AidlRenameResult.Failure(
                AidlRefactoringFailureKind.PROCESS,
                "AIDL compiler exited with unexpected status ${output.exitCode}",
            )
        }
        return try {
            parseRename(output.stdout, output.exitCode)
        } catch (exception: Exception) {
            AidlRenameResult.Failure(
                AidlRefactoringFailureKind.JSON,
                "invalid AIDL compiler rename JSON response: ${exception.message ?: exception::class.simpleName}",
            )
        }
    }

    private fun commandPrefix(projectPath: Path): List<String> = executable

    private fun run(command: List<String>, projectPath: Path) = try {
        val normalizedProject = projectPath.toAbsolutePath().normalize()
        val workingDirectory = when {
            Files.isDirectory(normalizedProject) -> normalizedProject
            normalizedProject.parent != null -> normalizedProject.parent
            else -> Path.of(".").toAbsolutePath().normalize()
        }
        processRunner.run(command, workingDirectory)
    } catch (_: Exception) {
        null
    }

    private fun parseUsages(text: String): AidlUsagesResult {
        val root = JsonParser.parseString(text).asObject("root")
        require(root.requiredString("command") == "usages") { "command must be 'usages'" }
        require(root.requiredBoolean("ok")) { "usages response must have ok=true" }
        val result = root.requiredObject("result")
        return when (result.requiredString("status")) {
            "unresolved", "ambiguous", "invalid" -> AidlUsagesResult.NoTarget
            "resolved" -> {
                val target = parseTarget(result.requiredObject("target"))
                val usagesElement = result.get("usages") ?: throw IllegalArgumentException("missing 'usages'")
                require(usagesElement.isJsonArray) { "'usages' must be an array" }
                AidlUsagesResult.Resolved(
                    target = target,
                    usages = usagesElement.asJsonArray.map { parseUsage(it.asObject("usage")) },
                )
            }
            else -> throw IllegalArgumentException("unknown usages status")
        }
    }

    private fun parseRename(text: String, exitCode: Int): AidlRenameResult {
        val root = JsonParser.parseString(text).asObject("root")
        require(root.requiredString("command") == "rename") { "command must be 'rename'" }
        val result = root.requiredObject("result")
        val status = result.requiredString("status")
        if (exitCode == 1) {
            require(!root.requiredBoolean("ok")) { "rejected rename must have ok=false" }
            return AidlRenameResult.Rejected(status, result.optionalString("message"))
        }
        require(root.requiredBoolean("ok")) { "successful rename must have ok=true" }
        require(status == "applied" && result.requiredBoolean("applied")) { "rename apply must report applied" }
        val editsElement = result.get("edits") ?: throw IllegalArgumentException("missing 'edits'")
        require(editsElement.isJsonArray) { "'edits' must be an array" }
        return AidlRenameResult.Applied(
            newFullyQualifiedName = result.requiredString("newFullyQualifiedName"),
            edits = editsElement.asJsonArray.map { parseUsage(it.asObject("edit")) },
        )
    }

    private fun parseTarget(target: JsonObject): AidlCompilerReferenceTarget {
        val location = target.requiredObject("location")
        return AidlCompilerReferenceTarget(
            fullyQualifiedName = target.requiredString("fullyQualifiedName"),
            kind = target.requiredString("kind"),
            location = AidlReferenceTargetLocation(
                file = location.requiredString("file"),
                line = location.requiredInt("line"),
                column = location.requiredInt("column"),
                offset = location.requiredInt("offset"),
            ),
        )
    }

    private fun parseUsage(usage: JsonObject): AidlUsageLocation = AidlUsageLocation(
        file = usage.requiredString("file"),
        line = usage.requiredInt("line"),
        column = usage.requiredInt("column"),
        offset = usage.requiredInt("offset"),
        length = usage.requiredInt("length"),
    )
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

private fun JsonObject.requiredInt(name: String): Int {
    val element = get(name) ?: throw IllegalArgumentException("missing '$name'")
    require(element.isJsonPrimitive && element.asJsonPrimitive.isNumber) { "'$name' must be a number" }
    return element.asInt
}

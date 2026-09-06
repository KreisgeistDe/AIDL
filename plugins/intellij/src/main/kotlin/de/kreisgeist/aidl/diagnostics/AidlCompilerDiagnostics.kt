package de.kreisgeist.aidl.diagnostics

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.nio.file.Files
import java.nio.file.Path
import kotlin.concurrent.thread

enum class AidlDiagnosticSeverity {
    ERROR,
    WARNING,
    INFO;

    companion object {
        fun fromWireValue(value: String): AidlDiagnosticSeverity =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) }
                ?: throw IllegalArgumentException("unknown diagnostic severity '$value'")
    }
}

data class AidlSourceLocation(
    val file: String,
    val line: Int,
    val column: Int,
    val offset: Int,
)

data class AidlDiagnosticSubject(
    val kind: String,
    val name: String,
)

data class AidlDiagnosticFix(
    val kind: String,
    val text: String,
)

data class AidlCompilerDiagnostic(
    val code: String,
    val phase: String,
    val severity: AidlDiagnosticSeverity,
    val message: String,
    val location: AidlSourceLocation,
    val subject: AidlDiagnosticSubject? = null,
    val expected: String? = null,
    val allowedFixes: List<AidlDiagnosticFix> = emptyList(),
    val docs: String? = null,
)

enum class AidlDiagnosticFailureKind {
    COMPILER,
    PROCESS,
    JSON,
}

sealed interface AidlDiagnosticResult {
    data class Success(
        val diagnostics: List<AidlCompilerDiagnostic>,
    ) : AidlDiagnosticResult

    data class Failure(
        val kind: AidlDiagnosticFailureKind,
        val message: String,
        val exitCode: Int? = null,
        val stderr: String = "",
    ) : AidlDiagnosticResult
}

data class AidlProcessOutput(
    val exitCode: Int,
    val stdout: String,
    val stderr: String,
)

fun interface AidlProcessRunner {
    fun run(command: List<String>, workingDirectory: Path): AidlProcessOutput
}

class DefaultAidlProcessRunner : AidlProcessRunner {
    override fun run(command: List<String>, workingDirectory: Path): AidlProcessOutput {
        val process = ProcessBuilder(command)
            .directory(workingDirectory.toFile())
            .start()
        var stdout = ""
        var stderr = ""
        val stdoutReader = thread(start = true, name = "aidl-diagnostics-stdout") {
            stdout = process.inputStream.bufferedReader().use { it.readText() }
        }
        val stderrReader = thread(start = true, name = "aidl-diagnostics-stderr") {
            stderr = process.errorStream.bufferedReader().use { it.readText() }
        }
        val exitCode = process.waitFor()
        stdoutReader.join()
        stderrReader.join()
        return AidlProcessOutput(exitCode, stdout, stderr)
    }
}

class AidlCompilerDiagnosticsAdapter(
    private val processRunner: AidlProcessRunner = DefaultAidlProcessRunner(),
    private val executable: List<String> = listOf("aidl"),
) {
    fun check(projectPath: Path): AidlDiagnosticResult {
        val normalizedProject = projectPath.toAbsolutePath().normalize()
        val workingDirectory = when {
            Files.isDirectory(normalizedProject) -> normalizedProject
            normalizedProject.parent != null -> normalizedProject.parent
            else -> Path.of(".").toAbsolutePath().normalize()
        }
        val command = executable + listOf(
            "check",
            normalizedProject.toString(),
            "--format",
            "json",
        )

        val output = try {
            processRunner.run(command, workingDirectory)
        } catch (exception: Exception) {
            return AidlDiagnosticResult.Failure(
                kind = AidlDiagnosticFailureKind.PROCESS,
                message = "failed to start or execute AIDL compiler: ${exception.message ?: exception::class.simpleName}",
            )
        }

        if (output.exitCode !in setOf(0, 1, 70)) {
            return AidlDiagnosticResult.Failure(
                kind = AidlDiagnosticFailureKind.PROCESS,
                message = "AIDL compiler exited with unexpected status ${output.exitCode}",
                exitCode = output.exitCode,
                stderr = output.stderr,
            )
        }

        val envelope = try {
            parseEnvelope(output.stdout)
        } catch (exception: Exception) {
            return AidlDiagnosticResult.Failure(
                kind = AidlDiagnosticFailureKind.JSON,
                message = "invalid AIDL compiler JSON response: ${exception.message ?: exception::class.simpleName}",
                exitCode = output.exitCode,
                stderr = output.stderr,
            )
        }

        if (output.exitCode == 70) {
            return AidlDiagnosticResult.Failure(
                kind = AidlDiagnosticFailureKind.COMPILER,
                message = envelope.errorMessage ?: "AIDL compiler reported an internal failure",
                exitCode = output.exitCode,
                stderr = output.stderr,
            )
        }

        val hasErrors = envelope.diagnostics.any { it.severity == AidlDiagnosticSeverity.ERROR }
        if (output.exitCode == 0 && (!envelope.ok || hasErrors)) {
            return inconsistentResponse(output, "exit 0 requires ok=true and no error diagnostics")
        }
        if (output.exitCode == 1 && (envelope.ok || !hasErrors)) {
            return inconsistentResponse(output, "exit 1 requires ok=false and at least one error diagnostic")
        }

        return AidlDiagnosticResult.Success(envelope.diagnostics)
    }

    private fun inconsistentResponse(output: AidlProcessOutput, detail: String): AidlDiagnosticResult.Failure =
        AidlDiagnosticResult.Failure(
            kind = AidlDiagnosticFailureKind.JSON,
            message = "invalid AIDL compiler JSON response: $detail",
            exitCode = output.exitCode,
            stderr = output.stderr,
        )

    private fun parseEnvelope(text: String): ParsedEnvelope {
        val root = JsonParser.parseString(text).asObject("root")
        require(root.requiredString("command") == "check") { "command must be 'check'" }
        val ok = root.requiredBoolean("ok")
        val diagnosticsElement = root.get("diagnostics")
            ?: throw IllegalArgumentException("missing 'diagnostics'")
        require(diagnosticsElement.isJsonArray) { "'diagnostics' must be an array" }
        val diagnostics = diagnosticsElement.asJsonArray.map(::parseDiagnostic)
        val errorMessage = root.get("error")
            ?.takeUnless { it.isJsonNull }
            ?.asObject("error")
            ?.optionalString("message")
        return ParsedEnvelope(ok, diagnostics, errorMessage)
    }

    private fun parseDiagnostic(element: JsonElement): AidlCompilerDiagnostic {
        val diagnostic = element.asObject("diagnostic")
        val location = diagnostic.requiredObject("location")
        val subject = diagnostic.get("subject")
            ?.takeUnless { it.isJsonNull }
            ?.asObject("subject")
            ?.let {
                AidlDiagnosticSubject(
                    kind = it.requiredString("kind"),
                    name = it.requiredString("name"),
                )
            }
        val allowedFixes = diagnostic.get("allowedFixes")
            ?.takeUnless { it.isJsonNull }
            ?.let { fixes ->
                require(fixes.isJsonArray) { "'allowedFixes' must be an array" }
                fixes.asJsonArray.map { fixElement ->
                    val fix = fixElement.asObject("allowedFixes item")
                    AidlDiagnosticFix(
                        kind = fix.requiredString("kind"),
                        text = fix.requiredString("text"),
                    )
                }
            }
            ?: emptyList()
        return AidlCompilerDiagnostic(
            code = diagnostic.requiredString("code"),
            phase = diagnostic.requiredString("phase"),
            severity = AidlDiagnosticSeverity.fromWireValue(diagnostic.requiredString("severity")),
            message = diagnostic.requiredString("message"),
            location = AidlSourceLocation(
                file = location.requiredString("file"),
                line = location.requiredInt("line"),
                column = location.requiredInt("column"),
                offset = location.requiredInt("offset"),
            ),
            subject = subject,
            expected = diagnostic.optionalString("expected"),
            allowedFixes = allowedFixes,
            docs = diagnostic.optionalString("docs"),
        )
    }

    private data class ParsedEnvelope(
        val ok: Boolean,
        val diagnostics: List<AidlCompilerDiagnostic>,
        val errorMessage: String?,
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

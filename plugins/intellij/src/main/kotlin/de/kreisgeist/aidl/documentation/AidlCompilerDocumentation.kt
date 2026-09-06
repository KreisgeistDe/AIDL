package de.kreisgeist.aidl.documentation

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import de.kreisgeist.aidl.diagnostics.DefaultAidlProcessRunner
import java.nio.file.Files
import java.nio.file.Path

data class AidlDocumentationLocation(
    val file: String,
    val line: Int,
    val column: Int,
    val offset: Int,
)

data class AidlDeclarationDocumentation(
    val fullyQualifiedName: String,
    val kind: String,
    val location: AidlDocumentationLocation,
    val representation: String,
)

data class AidlDocumentationSubject(val kind: String, val name: String)
data class AidlDocumentationFix(val kind: String, val text: String)

data class AidlDocumentationDiagnostic(
    val code: String,
    val phase: String,
    val severity: String,
    val message: String,
    val location: AidlDocumentationLocation,
    val subject: AidlDocumentationSubject?,
    val expected: String?,
    val docs: String?,
    val allowedFixes: List<AidlDocumentationFix>,
)

enum class AidlDocumentationFailureKind { PROCESS, COMPILER, JSON }

sealed interface AidlDocumentationResult {
    data class Resolved(
        val declaration: AidlDeclarationDocumentation?,
        val diagnostics: List<AidlDocumentationDiagnostic>,
    ) : AidlDocumentationResult

    data object NoDocumentation : AidlDocumentationResult
    data class Failure(val kind: AidlDocumentationFailureKind, val message: String) : AidlDocumentationResult
}

class AidlCompilerDocumentationAdapter(
    private val processRunner: AidlProcessRunner = DefaultAidlProcessRunner(),
    private val executable: List<String> = listOf("aidl"),
) {
    fun document(projectPath: Path, sourcePath: Path, offset: Int): AidlDocumentationResult {
        val normalizedProject = projectPath.toAbsolutePath().normalize()
        val normalizedSource = sourcePath.toAbsolutePath().normalize()
        val workingDirectory = when {
            Files.isDirectory(normalizedProject) -> normalizedProject
            normalizedProject.parent != null -> normalizedProject.parent
            else -> Path.of(".").toAbsolutePath().normalize()
        }
        val command = executable + listOf(
            "document",
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
            return AidlDocumentationResult.Failure(
                AidlDocumentationFailureKind.PROCESS,
                "failed to execute AIDL compiler: ${exception.message ?: exception::class.simpleName}",
            )
        }
        if (output.exitCode == 70) {
            return AidlDocumentationResult.Failure(
                AidlDocumentationFailureKind.COMPILER,
                "AIDL compiler reported an internal failure",
            )
        }
        if (output.exitCode != 0) {
            return AidlDocumentationResult.Failure(
                AidlDocumentationFailureKind.PROCESS,
                "AIDL compiler exited with unexpected status ${output.exitCode}",
            )
        }
        return try {
            parseEnvelope(output.stdout)
        } catch (exception: Exception) {
            AidlDocumentationResult.Failure(
                AidlDocumentationFailureKind.JSON,
                "invalid AIDL compiler documentation JSON response: ${exception.message ?: exception::class.simpleName}",
            )
        }
    }

    private fun parseEnvelope(text: String): AidlDocumentationResult {
        val root = JsonParser.parseString(text).asObject("root")
        require(root.requiredString("command") == "document") { "command must be 'document'" }
        require(root.requiredBoolean("ok")) { "document response must have ok=true" }
        val result = root.requiredObject("result")
        return when (result.requiredString("status")) {
            "invalid", "unresolved", "ambiguous" -> AidlDocumentationResult.NoDocumentation
            "resolved" -> {
                val declaration = result.get("declaration")
                    ?.takeUnless { it.isJsonNull }
                    ?.asObject("declaration")
                    ?.let(::parseDeclaration)
                val diagnosticsElement = result.get("diagnostics")
                    ?: throw IllegalArgumentException("missing 'diagnostics'")
                require(diagnosticsElement.isJsonArray) { "'diagnostics' must be an array" }
                val diagnostics = diagnosticsElement.asJsonArray.map(::parseDiagnostic)
                require(declaration != null || diagnostics.isNotEmpty()) {
                    "resolved documentation must contain declaration or diagnostics"
                }
                AidlDocumentationResult.Resolved(declaration, diagnostics)
            }
            else -> throw IllegalArgumentException("unknown documentation status")
        }
    }

    private fun parseDeclaration(value: JsonObject): AidlDeclarationDocumentation =
        AidlDeclarationDocumentation(
            fullyQualifiedName = value.requiredString("fullyQualifiedName"),
            kind = value.requiredString("kind"),
            location = parseLocation(value.requiredObject("location")),
            representation = value.requiredString("representation"),
        )

    private fun parseDiagnostic(element: JsonElement): AidlDocumentationDiagnostic {
        val value = element.asObject("diagnostic")
        val subject = value.get("subject")
            ?.takeUnless { it.isJsonNull }
            ?.asObject("subject")
            ?.let { AidlDocumentationSubject(it.requiredString("kind"), it.requiredString("name")) }
        val fixes = value.get("allowedFixes")
            ?.takeUnless { it.isJsonNull }
            ?.let { fixesElement ->
                require(fixesElement.isJsonArray) { "'allowedFixes' must be an array" }
                fixesElement.asJsonArray.map { fixElement ->
                    val fix = fixElement.asObject("allowedFixes item")
                    AidlDocumentationFix(fix.requiredString("kind"), fix.requiredString("text"))
                }
            }
            ?: emptyList()
        return AidlDocumentationDiagnostic(
            code = value.requiredString("code"),
            phase = value.requiredString("phase"),
            severity = value.requiredString("severity"),
            message = value.requiredString("message"),
            location = parseLocation(value.requiredObject("location")),
            subject = subject,
            expected = value.optionalString("expected"),
            docs = value.optionalString("docs"),
            allowedFixes = fixes,
        )
    }

    private fun parseLocation(value: JsonObject): AidlDocumentationLocation =
        AidlDocumentationLocation(
            file = value.requiredString("file"),
            line = value.requiredInt("line"),
            column = value.requiredInt("column"),
            offset = value.requiredInt("offset"),
        )
}

object AidlCompilerDocumentationRenderer {
    fun render(result: AidlDocumentationResult.Resolved): String {
        val html = StringBuilder()
        result.declaration?.let { declaration ->
            html.append("<div class='definition'><pre>")
            html.append(escape(declaration.representation))
            html.append("</pre></div>")
            html.append("<div class='content'>")
            html.append("<p><b>").append(escape(declaration.fullyQualifiedName)).append("</b>")
            html.append(" · ").append(escape(declaration.kind)).append("</p>")
            html.append("<p>").append(escape(locationText(declaration.location))).append("</p>")
            html.append("</div>")
        }
        result.diagnostics.forEach { diagnostic ->
            html.append("<div class='content'>")
            html.append("<p><b>").append(escape(diagnostic.code)).append("</b>")
            html.append(" · ").append(escape(diagnostic.phase))
            html.append(" · ").append(escape(diagnostic.severity)).append("</p>")
            html.append("<p>").append(escape(diagnostic.message)).append("</p>")
            diagnostic.subject?.let {
                html.append("<p>Subject: ").append(escape("${it.kind} ${it.name}")).append("</p>")
            }
            diagnostic.expected?.let {
                html.append("<p>Expected: ").append(escape(it)).append("</p>")
            }
            diagnostic.docs?.let {
                html.append("<p>Docs: ").append(escape(it)).append("</p>")
            }
            if (diagnostic.allowedFixes.isNotEmpty()) {
                html.append("<p>Allowed fixes:</p><ul>")
                diagnostic.allowedFixes.forEach { fix ->
                    html.append("<li>").append(escape("${fix.kind}: ${fix.text}")).append("</li>")
                }
                html.append("</ul>")
            }
            html.append("<p>").append(escape(locationText(diagnostic.location))).append("</p>")
            html.append("</div>")
        }
        return html.toString()
    }

    private fun locationText(location: AidlDocumentationLocation): String =
        "${location.file}:${location.line}:${location.column}"

    private fun escape(value: String): String = buildString(value.length) {
        value.forEach { character ->
            append(
                when (character) {
                    '&' -> "&amp;"
                    '<' -> "&lt;"
                    '>' -> "&gt;"
                    '"' -> "&quot;"
                    '\'' -> "&#39;"
                    else -> character.toString()
                },
            )
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

private fun JsonObject.requiredInt(name: String): Int {
    val element = get(name) ?: throw IllegalArgumentException("missing '$name'")
    require(element.isJsonPrimitive && element.asJsonPrimitive.isNumber) { "'$name' must be a number" }
    return element.asInt
}

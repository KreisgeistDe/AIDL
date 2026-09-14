package de.kreisgeist.aidl.compiler.frontend

class ProjectedTypeException(message: String) : IllegalArgumentException(message)

internal enum class ProjectedTypeDiagnosticSeverity {
    ERROR,
}

internal data class ProjectedTypeDiagnosticSubject(
    val kind: String,
    val name: String,
)

internal data class ProjectedTypeDiagnostic(
    val code: String,
    val phase: String,
    val severity: ProjectedTypeDiagnosticSeverity,
    val message: String,
    val sourcePath: String,
    val location: ProjectedSourceLocation,
    val subject: ProjectedTypeDiagnosticSubject,
    val expected: String,
    val docs: String,
)

internal data class ProjectedTypeDiagnosticRequest(
    val diagnosticOffset: Int,
    val subjectKind: String,
    val subjectName: String,
    val typeSource: String,
)

enum class ProjectedTypeResolutionStatus {
    RESOLVED,
    UNRESOLVED,
    AMBIGUOUS,
}

data class ProjectedTypeRange(
    val min: String,
    val max: String,
)

data class ProjectedTypeRef(
    val name: String? = null,
    val elementType: ProjectedTypeRef? = null,
    val nullable: Boolean = false,
    val range: ProjectedTypeRange? = null,
) {
    init {
        require((name == null) != (elementType == null)) { "type must have exactly one base shape" }
        require(elementType == null || range == null) { "list type cannot carry a range" }
    }

    val isList: Boolean
        get() = elementType != null

    fun stableSignature(): String = buildString {
        if (elementType != null) {
            append('[').append(elementType.stableSignature()).append(']')
        } else {
            append(name)
            range?.let { append('(').append(it.min).append("..").append(it.max).append(')') }
        }
        if (nullable) append('?')
    }
}

data class ProjectedTypeCheck(
    val status: ProjectedTypeResolutionStatus,
    val type: ProjectedTypeRef,
    val symbols: List<ProjectedSymbol>,
)

data class ProjectedTypeMaterialization(
    val signature: String,
    val nullable: Boolean,
    val baseName: String?,
    val elementSignature: String?,
    val rangeMin: String?,
    val rangeMax: String?,
    val symbolIdentities: List<String>,
)

/**
 * Third bounded M10.5-03 front-end slice.
 *
 * This layer deliberately mirrors only the frozen revision-4 TypeRef facts needed after
 * SourceProjection and NameResolution: named/builtin references, list shape, optionality,
 * structured min..max range, deterministic name checking, and deterministic materialization.
 * Generic arguments and non-range constraint syntax fail closed; they are not Kotlin support.
 */
object ProjectedTypeConstructor {
    private const val typeDiagnosticCode = "AIDL-T001"
    private const val typeDiagnosticPhase = "type"
    private const val typeDiagnosticExpected = "well-formed Core type constructor"
    private const val typeDiagnosticDocs = "aidl://diagnostics/AIDL-T001"

    private val builtins = setOf(
        "bool", "bytes", "date", "datetime", "decimal", "duration", "email", "float",
        "int", "json", "long", "revision", "string", "time", "url", "uuid",
    )
    private val number = Regex("-?[0-9]+(?:\\.[0-9]+)?")
    private val identifier = Regex("[A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*")

    fun construct(source: String): ProjectedTypeRef {
        val text = source.trim()
        if (text.isEmpty()) throw ProjectedTypeException("empty type expression")
        if ('<' in text || '>' in text) throw ProjectedTypeException("generic type arguments are outside the bounded revision-4 slice")

        var core = text
        val nullable = core.endsWith('?')
        if (nullable) core = core.dropLast(1).trimEnd()
        if (core.endsWith('?')) throw ProjectedTypeException("nullable requires one non-nullable operand")

        if (core.startsWith('[')) {
            if (!core.endsWith(']')) throw ProjectedTypeException("list requires one element type")
            val nested = core.substring(1, core.length - 1).trim()
            if (nested.isEmpty()) throw ProjectedTypeException("list requires one element type")
            return ProjectedTypeRef(elementType = construct(nested), nullable = nullable)
        }
        if ('[' in core || ']' in core) throw ProjectedTypeException("invalid Core type expression '$core'")

        val open = core.indexOf('(')
        val range = if (open >= 0) {
            if (!core.endsWith(')')) throw ProjectedTypeException("unterminated type modifier")
            val payload = core.substring(open + 1, core.length - 1).trim()
            val parts = payload.split("..")
            if (parts.size != 2 || parts.any { !number.matches(it.trim()) }) {
                throw ProjectedTypeException("only structured min..max range modifiers are supported")
            }
            core = core.substring(0, open).trimEnd()
            ProjectedTypeRange(parts[0].trim(), parts[1].trim())
        } else {
            if ('(' in core || ')' in core || ',' in core || ':' in core) {
                throw ProjectedTypeException("non-range type constraints are outside the bounded revision-4 slice")
            }
            null
        }

        if (!identifier.matches(core)) throw ProjectedTypeException("invalid type name '$core'")
        return ProjectedTypeRef(name = core, nullable = nullable, range = range)
    }

    /**
     * Internal structured diagnostic projection for callers that already own a source anchor.
     *
     * The Python reference maps TypeSyntaxError through its existing type-checking diagnostic
     * machinery to AIDL-T001/type/error with declaration subject, source span, expected payload,
     * and stable docs URI. This helper mirrors exactly that observable without changing syntax,
     * acceptance, resolution, or the public TypeConstruction surface.
     */
    internal fun diagnosticAt(
        sourcePath: String,
        sourceText: String,
        diagnosticOffset: Int,
        subjectKind: String,
        subjectName: String,
        typeSource: String,
    ): ProjectedTypeDiagnostic? {
        require(diagnosticOffset in 0..sourceText.length) { "diagnostic offset is outside source text" }
        return try {
            construct(typeSource)
            null
        } catch (error: ProjectedTypeException) {
            ProjectedTypeDiagnostic(
                code = typeDiagnosticCode,
                phase = typeDiagnosticPhase,
                severity = ProjectedTypeDiagnosticSeverity.ERROR,
                message = error.message!!,
                sourcePath = sourcePath,
                location = sourceLocation(sourceText, diagnosticOffset),
                subject = ProjectedTypeDiagnosticSubject(subjectKind, subjectName),
                expected = typeDiagnosticExpected,
                docs = typeDiagnosticDocs,
            )
        }
    }

    internal fun diagnosticsAt(
        sourcePath: String,
        sourceText: String,
        requests: List<ProjectedTypeDiagnosticRequest>,
    ): List<ProjectedTypeDiagnostic> = requests.mapNotNull { request ->
        diagnosticAt(
            sourcePath = sourcePath,
            sourceText = sourceText,
            diagnosticOffset = request.diagnosticOffset,
            subjectKind = request.subjectKind,
            subjectName = request.subjectName,
            typeSource = request.typeSource,
        )
    }.sortedWith(
        compareBy<ProjectedTypeDiagnostic> { it.location.offset }
            .thenBy { it.phase }
            .thenBy { it.severity.ordinal }
            .thenBy { it.code }
            .thenBy { it.message },
    )

    fun check(sourceId: String, source: String, resolver: ProjectNameResolver): ProjectedTypeCheck {
        val type = construct(source)
        val symbols = mutableListOf<ProjectedSymbol>()
        var status = ProjectedTypeResolutionStatus.RESOLVED

        fun visit(current: ProjectedTypeRef) {
            current.elementType?.let { visit(it); return }
            val name = current.name ?: return
            if (name in builtins) return
            val resolution = resolver.resolve(sourceId, name)
            symbols += resolution.symbols
            val candidateStatus = when (resolution.status) {
                ProjectedResolutionStatus.RESOLVED -> ProjectedTypeResolutionStatus.RESOLVED
                ProjectedResolutionStatus.UNRESOLVED -> ProjectedTypeResolutionStatus.UNRESOLVED
                ProjectedResolutionStatus.AMBIGUOUS -> ProjectedTypeResolutionStatus.AMBIGUOUS
            }
            if (candidateStatus == ProjectedTypeResolutionStatus.AMBIGUOUS ||
                status == ProjectedTypeResolutionStatus.RESOLVED && candidateStatus == ProjectedTypeResolutionStatus.UNRESOLVED
            ) {
                status = candidateStatus
            }
        }
        visit(type)
        return ProjectedTypeCheck(status, type, symbols.distinctBy { it.sourceId to it.declarationIndex })
    }

    fun materialize(check: ProjectedTypeCheck): ProjectedTypeMaterialization {
        val type = check.type
        return ProjectedTypeMaterialization(
            signature = type.stableSignature(),
            nullable = type.nullable,
            baseName = type.name,
            elementSignature = type.elementType?.stableSignature(),
            rangeMin = type.range?.min,
            rangeMax = type.range?.max,
            symbolIdentities = check.symbols.mapNotNull { it.stableIdentity },
        )
    }

    private fun sourceLocation(source: String, offset: Int): ProjectedSourceLocation {
        var line = 1
        var column = 1
        for (index in 0 until offset) {
            if (source[index] == '\n') {
                line += 1
                column = 1
            } else {
                column += 1
            }
        }
        return ProjectedSourceLocation(line = line, column = column, offset = offset)
    }
}

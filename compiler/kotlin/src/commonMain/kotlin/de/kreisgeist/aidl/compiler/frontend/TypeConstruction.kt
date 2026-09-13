package de.kreisgeist.aidl.compiler.frontend

class ProjectedTypeException(message: String) : IllegalArgumentException(message)

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
    private val builtins = setOf(
        "bool", "bytes", "date", "datetime", "decimal", "duration", "email", "float",
        "int", "json", "long", "revision", "string", "time", "url", "uuid",
    )
    private val number = Regex("-?[0-9]+(?:\\.[0-9]+)?")
    private val identifier = Regex("[A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*")

    fun construct(source: String): ProjectedTypeRef {
        val text = source.trim()
        if (text.isEmpty()) throw ProjectedTypeException("type reference must not be blank")
        if ('<' in text || '>' in text) throw ProjectedTypeException("generic type arguments are outside the bounded revision-4 slice")

        var core = text
        val nullable = core.endsWith('?')
        if (nullable) core = core.dropLast(1).trimEnd()
        if (core.endsWith('?')) throw ProjectedTypeException("duplicate optional marker")

        if (core.startsWith('[')) {
            if (!core.endsWith(']')) throw ProjectedTypeException("unterminated list type")
            val nested = core.substring(1, core.length - 1).trim()
            if (nested.isEmpty()) throw ProjectedTypeException("list element type must not be blank")
            return ProjectedTypeRef(elementType = construct(nested), nullable = nullable)
        }
        if ('[' in core || ']' in core) throw ProjectedTypeException("invalid list type shape")

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
}

package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedSerializationStatus {
    SERIALIZABLE,
    NOT_SERIALIZABLE,
    UNRESOLVED,
    AMBIGUOUS,
    OUTSIDE_SLICE,
}

data class ProjectedSerializationCheck(
    val status: ProjectedSerializationStatus,
    val diagnosticCode: String? = null,
)

/**
 * Bounded M10.5-03 serialization-check parity over the already integrated type/resolution slice.
 *
 * This does not define wire semantics. Direct Core remains semantic authority and Python remains
 * compatibility/conformance evidence. The slice mirrors the current Python public-wire observable
 * only for scalar/list/nullable shapes, empty nominal enum/entity/value declarations, and resolved
 * entity refs, which the current Python serializer rejects for public wire use. More complex value
 * recursion and materialization stay outside this package.
 */
object ProjectedSerializationChecker {
    private val serialScalars = setOf(
        "bool", "bytes", "date", "datetime", "decimal", "duration", "email", "int",
        "revision", "string", "url", "uuid",
    )
    private val boundedRef = Regex("ref\\s+([A-Za-z_][A-Za-z0-9_.]*)")
    private const val historicalGenericBoundary =
        "generic type arguments are outside the bounded revision-4 slice"

    fun check(
        sourceId: String,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedSerializationCheck {
        val text = typeSource.trim()
        boundedRef.matchEntire(text)?.let { match ->
            val resolution = resolver.resolve(sourceId, match.groupValues[1])
            return when (resolution.status) {
                ProjectedResolutionStatus.AMBIGUOUS ->
                    ProjectedSerializationCheck(ProjectedSerializationStatus.AMBIGUOUS, "CORE-S023")
                ProjectedResolutionStatus.UNRESOLVED ->
                    ProjectedSerializationCheck(ProjectedSerializationStatus.UNRESOLVED, "AIDL-T001")
                ProjectedResolutionStatus.RESOLVED -> if (resolution.symbols.single().kind == "entity") {
                    ProjectedSerializationCheck(ProjectedSerializationStatus.NOT_SERIALIZABLE, "AIDL-T004")
                } else {
                    ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
                }
            }
        }
        if (text.startsWith("ref ")) {
            return ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
        }

        val typeCheck = try {
            ProjectedTypeConstructor.check(sourceId, typeSource, resolver)
        } catch (error: ProjectedTypeException) {
            if (error.message == historicalGenericBoundary) {
                return ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
            }
            throw error
        }

        when (typeCheck.status) {
            ProjectedTypeResolutionStatus.AMBIGUOUS ->
                return ProjectedSerializationCheck(ProjectedSerializationStatus.AMBIGUOUS, "CORE-S023")
            ProjectedTypeResolutionStatus.UNRESOLVED ->
                return ProjectedSerializationCheck(ProjectedSerializationStatus.UNRESOLVED, "AIDL-T001")
            ProjectedTypeResolutionStatus.RESOLVED -> Unit
        }

        return classify(typeCheck.type, typeCheck.symbols.singleOrNull(), resolver)
    }

    private fun classify(
        type: ProjectedTypeRef,
        symbol: ProjectedSymbol?,
        resolver: ProjectNameResolver,
    ): ProjectedSerializationCheck {
        type.elementType?.let { element ->
            return classify(element, symbol, resolver)
        }
        val name = type.name ?: return ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
        if (name in serialScalars) {
            return ProjectedSerializationCheck(ProjectedSerializationStatus.SERIALIZABLE)
        }
        if (symbol == null) {
            return ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
        }

        val declaration = resolver.documents
            .first { it.sourceId == symbol.sourceId }
            .projection.declarations[symbol.declarationIndex]
        return when (symbol.kind) {
            "enum", "entity" -> ProjectedSerializationCheck(ProjectedSerializationStatus.SERIALIZABLE)
            "value" -> if (declaration.bodyTokens.isEmpty()) {
                ProjectedSerializationCheck(ProjectedSerializationStatus.SERIALIZABLE)
            } else {
                ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
            }
            else -> ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
        }
    }
}

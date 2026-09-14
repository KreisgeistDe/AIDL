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
 * only for scalar/list/nullable shapes, empty nominal enum/entity/value declarations, and the
 * existing sensitive-value rejection. More complex value-field recursion and materialization stay
 * outside this package.
 */
object ProjectedSerializationChecker {
    private val serialScalars = setOf(
        "bool", "bytes", "date", "datetime", "decimal", "duration", "email", "int",
        "revision", "string", "url", "uuid",
    )
    private const val historicalGenericBoundary =
        "generic type arguments are outside the bounded revision-4 slice"

    fun check(
        sourceId: String,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedSerializationCheck {
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
            "value" -> when {
                declaration.bodyTokens.isEmpty() ->
                    ProjectedSerializationCheck(ProjectedSerializationStatus.SERIALIZABLE)
                "sensitive" in declaration.bodyTokens ->
                    ProjectedSerializationCheck(ProjectedSerializationStatus.NOT_SERIALIZABLE, "AIDL-T004")
                else -> ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
            }
            else -> ProjectedSerializationCheck(ProjectedSerializationStatus.OUTSIDE_SLICE)
        }
    }
}

package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedMaterializationStatus {
    MATERIALIZABLE,
    REJECTED,
    UNRESOLVED,
    AMBIGUOUS,
    OUTSIDE_SLICE,
}

data class ProjectedMaterializationCheck(
    val status: ProjectedMaterializationStatus,
    val diagnosticCode: String? = null,
)

/**
 * Bounded M10.5-03 materialization-boundary parity over the integrated type/resolution surface.
 *
 * Direct Core remains semantic authority and Python remains compatibility/conformance evidence.
 * This slice mirrors the current Python Core-materialization observable that rejects resolved
 * project generic nominal targets with AIDL-T005 while preserving known Core standard generics.
 * Generic forms that are valid in direct Core but cannot be resolved by the historical bounded
 * Kotlin projector remain OUTSIDE_SLICE rather than becoming language errors.
 */
object ProjectedMaterializationChecker {
    private val standardTypes = setOf(
        "Page", "PageInput", "Cursor", "OperationId", "PrincipalId", "SubjectId",
        "FieldError", "FieldErrors", "ProblemDetails", "Unit",
    )
    private val materializedKinds = setOf("enum", "value", "entity")
    private val genericHead = Regex("([A-Za-z_][A-Za-z0-9_.]*)\\s*<(.*)>")

    fun check(
        sourceId: String,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedMaterializationCheck {
        val text = typeSource.trim()
        if ('<' in text || '>' in text) {
            return checkGeneric(sourceId, text, resolver, composeResolution = true)
        }

        val typeCheck = ProjectedTypeConstructor.check(sourceId, typeSource, resolver)
        return when (typeCheck.status) {
            ProjectedTypeResolutionStatus.AMBIGUOUS ->
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023")
            ProjectedTypeResolutionStatus.UNRESOLVED ->
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001")
            ProjectedTypeResolutionStatus.RESOLVED ->
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.MATERIALIZABLE)
        }
    }

    private fun checkGeneric(
        sourceId: String,
        text: String,
        resolver: ProjectNameResolver,
        composeResolution: Boolean,
    ): ProjectedMaterializationCheck {
        val shape = parseGeneric(text)
            ?: return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)

        if (shape.name in standardTypes) {
            val nested = shape.arguments.map { argument ->
                checkMaterializationOnly(sourceId, argument, resolver)
            }
            nested.firstOrNull { it.status == ProjectedMaterializationStatus.REJECTED }?.let { return it }
            if (nested.any { it.status != ProjectedMaterializationStatus.MATERIALIZABLE }) {
                return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
            return ProjectedMaterializationCheck(ProjectedMaterializationStatus.MATERIALIZABLE)
        }

        val resolution = resolver.resolve(sourceId, shape.name)
        return when (resolution.status) {
            ProjectedResolutionStatus.AMBIGUOUS -> if (composeResolution) {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023")
            } else {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
            ProjectedResolutionStatus.UNRESOLVED -> if (composeResolution) {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001")
            } else {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
            ProjectedResolutionStatus.RESOLVED -> if (resolution.symbols.single().kind in materializedKinds) {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005")
            } else {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
        }
    }

    private fun checkMaterializationOnly(
        sourceId: String,
        source: String,
        resolver: ProjectNameResolver,
    ): ProjectedMaterializationCheck {
        val text = source.trim()
        if ('<' in text || '>' in text) {
            return checkGeneric(sourceId, text, resolver, composeResolution = false)
        }
        return try {
            val check = ProjectedTypeConstructor.check(sourceId, text, resolver)
            if (check.status == ProjectedTypeResolutionStatus.RESOLVED) {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.MATERIALIZABLE)
            } else {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
        } catch (_: ProjectedTypeException) {
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
        }
    }

    private data class GenericShape(val name: String, val arguments: List<String>)

    private fun parseGeneric(text: String): GenericShape? {
        val match = genericHead.matchEntire(text) ?: return null
        val body = match.groupValues[2]
        val arguments = mutableListOf<String>()
        val buffer = StringBuilder()
        var depth = 0
        for (char in body) {
            when (char) {
                '<' -> { depth += 1; buffer.append(char) }
                '>' -> {
                    if (depth == 0) return null
                    depth -= 1
                    buffer.append(char)
                }
                ',' -> if (depth == 0) {
                    val argument = buffer.toString().trim()
                    if (argument.isEmpty()) return null
                    arguments += argument
                    buffer.clear()
                } else {
                    buffer.append(char)
                }
                else -> buffer.append(char)
            }
        }
        if (depth != 0) return null
        val last = buffer.toString().trim()
        if (last.isEmpty()) return null
        arguments += last
        return GenericShape(match.groupValues[1], arguments)
    }
}

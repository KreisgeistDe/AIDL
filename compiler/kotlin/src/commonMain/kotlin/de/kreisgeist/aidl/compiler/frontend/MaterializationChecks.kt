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
 * project generic nominal targets with AIDL-T005 while preserving known one-argument Core
 * standard generics. Direct-Core-valid generic forms that the historical projector cannot resolve
 * remain OUTSIDE_SLICE rather than becoming language errors.
 */
object ProjectedMaterializationChecker {
    private val standardTypes = setOf(
        "Page", "PageInput", "Cursor", "OperationId", "PrincipalId", "SubjectId",
        "FieldError", "FieldErrors", "ProblemDetails", "Unit",
    )
    private val genericHead = Regex("([A-Za-z_][A-Za-z0-9_.]*)\\s*<(.*)>")

    fun check(
        sourceId: String,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedMaterializationCheck {
        val text = typeSource.trim()
        if ('<' in text || '>' in text) {
            val shape = genericShape(text)
                ?: return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            if (shape.first in standardTypes) {
                val nested = materializationOnly(sourceId, shape.second, resolver)
                if (nested.status == ProjectedMaterializationStatus.REJECTED) return nested
                if (nested.status == ProjectedMaterializationStatus.MATERIALIZABLE) return nested
                return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
            val resolution = resolver.resolve(sourceId, shape.first)
            return when (resolution.status) {
                ProjectedResolutionStatus.AMBIGUOUS ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023")
                ProjectedResolutionStatus.UNRESOLVED ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001")
                ProjectedResolutionStatus.RESOLVED ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005")
            }
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

    private fun materializationOnly(
        sourceId: String,
        source: String,
        resolver: ProjectNameResolver,
    ): ProjectedMaterializationCheck {
        val text = source.trim()
        if ('<' in text || '>' in text) {
            val shape = genericShape(text)
                ?: return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            if (shape.first in standardTypes) {
                return materializationOnly(sourceId, shape.second, resolver)
            }
            return if (resolver.resolve(sourceId, shape.first).status == ProjectedResolutionStatus.RESOLVED) {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005")
            } else {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
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

    private fun genericShape(text: String): Pair<String, String>? {
        val match = genericHead.matchEntire(text) ?: return null
        val argument = match.groupValues[2].trim()
        if (argument.isEmpty() || ',' in argument) return null
        return match.groupValues[1] to argument
    }
}

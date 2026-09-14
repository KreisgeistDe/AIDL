package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedAssignmentStatus {
    ASSIGNABLE,
    TYPE_MISMATCH,
    UNRESOLVED,
    AMBIGUOUS,
    OUTSIDE_SLICE,
}

data class ProjectedAssignmentCheck(
    val status: ProjectedAssignmentStatus,
    val diagnosticCode: String? = null,
)

/**
 * Bounded M10.5-03 type-checking parity for operation default literals.
 *
 * This mirrors only the current Python compatibility/conformance observable:
 * null is assignable only to nullable types; non-null scalar literals require an
 * exact scalar match except that int is assignable to decimal. Direct Core remains
 * semantic authority. Resolution ambiguity fails closed with CORE-S023, and shapes
 * outside this deliberately small slice are not promoted to Kotlin support.
 */
object ProjectedTypeChecker {
    private val scalarNames = setOf("bool", "decimal", "int", "string")
    private val integer = Regex("-?[0-9]+")
    private val decimal = Regex("-?[0-9]+\\.[0-9]+")
    private val stringLiteral = Regex("\"(?:[^\"\\\\]|\\\\.)*\"")

    fun checkDefault(
        sourceId: String,
        typeSource: String,
        literalSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedAssignmentCheck {
        val typeCheck = ProjectedTypeConstructor.check(sourceId, typeSource, resolver)
        when (typeCheck.status) {
            ProjectedTypeResolutionStatus.AMBIGUOUS ->
                return ProjectedAssignmentCheck(ProjectedAssignmentStatus.AMBIGUOUS, "CORE-S023")
            ProjectedTypeResolutionStatus.UNRESOLVED ->
                return ProjectedAssignmentCheck(ProjectedAssignmentStatus.UNRESOLVED, "AIDL-T001")
            ProjectedTypeResolutionStatus.RESOLVED -> Unit
        }

        val type = typeCheck.type
        val typeName = type.name
        if (type.isList || type.range != null || typeName == null || typeName !in scalarNames) {
            return ProjectedAssignmentCheck(ProjectedAssignmentStatus.OUTSIDE_SLICE)
        }

        val literalKind = literalKind(literalSource)
        if (literalKind == "null") {
            return if (type.nullable) {
                ProjectedAssignmentCheck(ProjectedAssignmentStatus.ASSIGNABLE)
            } else {
                ProjectedAssignmentCheck(ProjectedAssignmentStatus.TYPE_MISMATCH, "AIDL-T002")
            }
        }
        if (literalKind == null) {
            return ProjectedAssignmentCheck(ProjectedAssignmentStatus.OUTSIDE_SLICE)
        }

        val assignable = literalKind == typeName || typeName == "decimal" && literalKind == "int"
        return if (assignable) {
            ProjectedAssignmentCheck(ProjectedAssignmentStatus.ASSIGNABLE)
        } else {
            ProjectedAssignmentCheck(ProjectedAssignmentStatus.TYPE_MISMATCH, "AIDL-T002")
        }
    }

    private fun literalKind(source: String): String? {
        val text = source.trim()
        return when {
            text == "null" -> "null"
            text == "true" || text == "false" -> "bool"
            integer.matches(text) -> "int"
            decimal.matches(text) -> "decimal"
            stringLiteral.matches(text) -> "string"
            else -> null
        }
    }
}

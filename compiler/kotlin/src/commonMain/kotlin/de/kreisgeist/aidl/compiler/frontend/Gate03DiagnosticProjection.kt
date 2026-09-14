package de.kreisgeist.aidl.compiler.frontend

internal data class ProjectedGate03Diagnostic(
    val code: String,
    val sourcePath: String? = null,
    val location: ProjectedSourceLocation? = null,
)

/**
 * Bounded M10.5-03 certification projection over already-owned front-end semantics.
 *
 * This object does not invent diagnostic meaning or source anchors. Materialization and default
 * assignment diagnostics use the caller-owned declaration anchor that matches the current Python
 * issue contract. Resolver classifications remain location-less because the current authoritative
 * resolver evidence owns no diagnostic location for unresolved or ambiguous references.
 */
internal object ProjectedGate03DiagnosticProjector {
    fun materialization(
        sourceId: String,
        sourceText: String,
        diagnosticOffset: Int,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedGate03Diagnostic? {
        val check = ProjectedMaterializationChecker.checkAt(
            sourceId = sourceId,
            sourceText = sourceText,
            diagnosticOffset = diagnosticOffset,
            typeSource = typeSource,
            resolver = resolver,
        )
        val code = check.diagnosticCode ?: return null
        return ProjectedGate03Diagnostic(code, check.sourcePath, check.location)
    }

    fun resolution(
        sourceId: String,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedGate03Diagnostic? {
        val code = when (resolver.resolve(sourceId, typeSource).status) {
            ProjectedResolutionStatus.RESOLVED -> null
            ProjectedResolutionStatus.UNRESOLVED -> "AIDL-T001"
            ProjectedResolutionStatus.AMBIGUOUS -> "CORE-S023"
        } ?: return null
        return ProjectedGate03Diagnostic(code)
    }

    fun defaultAssignment(
        sourceId: String,
        sourceText: String,
        diagnosticOffset: Int,
        typeSource: String,
        literalSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedGate03Diagnostic? {
        require(diagnosticOffset in 0..sourceText.length) { "diagnostic offset is outside source text" }
        val check = ProjectedTypeChecker.checkDefault(sourceId, typeSource, literalSource, resolver)
        val code = check.diagnosticCode ?: return null
        if (code != "AIDL-T002") return ProjectedGate03Diagnostic(code)
        return ProjectedGate03Diagnostic(
            code = code,
            sourcePath = sourceId,
            location = sourceLocation(sourceText, diagnosticOffset),
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
        return ProjectedSourceLocation(line, column, offset)
    }
}

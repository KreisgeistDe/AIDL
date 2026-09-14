package de.kreisgeist.aidl.compiler.frontend

internal data class ProjectedDiagnosticTokenSpan(
    val start: ProjectedSourceLocation,
    val end: ProjectedSourceLocation,
    val stdoutLocation: String,
)

internal data class ProjectedGate03Diagnostic(
    val code: String,
    val span: ProjectedDiagnosticTokenSpan,
)

/**
 * Bounded M10.5-03 certification projection over already-owned front-end semantics.
 *
 * This object does not invent diagnostic meaning. Materialization, resolution and default
 * assignment classification remain owned by their existing checkers. The only additional fact
 * projected here is the exact TypeRef token span supplied by the caller, including an exclusive
 * end anchor and the deterministic text location used by parity certification.
 */
internal object ProjectedGate03DiagnosticProjector {
    fun materialization(
        sourceId: String,
        sourceText: String,
        typeOffset: Int,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedGate03Diagnostic? {
        val check = ProjectedMaterializationChecker.check(sourceId, typeSource, resolver)
        val code = check.diagnosticCode ?: return null
        return ProjectedGate03Diagnostic(code, tokenSpan(sourceId, sourceText, typeOffset, typeSource))
    }

    fun resolution(
        sourceId: String,
        sourceText: String,
        typeOffset: Int,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedGate03Diagnostic? {
        val code = when (resolver.resolve(sourceId, typeSource).status) {
            ProjectedResolutionStatus.RESOLVED -> null
            ProjectedResolutionStatus.UNRESOLVED -> "AIDL-T001"
            ProjectedResolutionStatus.AMBIGUOUS -> "CORE-S023"
        } ?: return null
        return ProjectedGate03Diagnostic(code, tokenSpan(sourceId, sourceText, typeOffset, typeSource))
    }

    fun defaultAssignment(
        sourceId: String,
        sourceText: String,
        typeOffset: Int,
        typeSource: String,
        literalSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedGate03Diagnostic? {
        val check = ProjectedTypeChecker.checkDefault(sourceId, typeSource, literalSource, resolver)
        val code = check.diagnosticCode ?: return null
        return ProjectedGate03Diagnostic(code, tokenSpan(sourceId, sourceText, typeOffset, typeSource))
    }

    private fun tokenSpan(
        sourceId: String,
        sourceText: String,
        typeOffset: Int,
        typeSource: String,
    ): ProjectedDiagnosticTokenSpan {
        require(typeOffset >= 0 && typeOffset + typeSource.length <= sourceText.length) {
            "TypeRef token span is outside source text"
        }
        require(sourceText.substring(typeOffset, typeOffset + typeSource.length) == typeSource) {
            "TypeRef token span does not match source text"
        }
        val start = sourceLocation(sourceText, typeOffset)
        val end = sourceLocation(sourceText, typeOffset + typeSource.length)
        return ProjectedDiagnosticTokenSpan(
            start = start,
            end = end,
            stdoutLocation = "$sourceId:${start.line}:${start.column}-${end.line}:${end.column}",
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

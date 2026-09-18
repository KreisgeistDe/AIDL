package de.kreisgeist.aidl.compiler.frontend

data class ProjectedAllowedDiagnosticFix(
    val kind: String,
    val text: String,
)

data class ProjectedAuthorizedFixDiagnostic(
    val code: String,
    val sourceId: String,
    val offset: Int,
    val allowedFixes: List<ProjectedAllowedDiagnosticFix> = emptyList(),
)

data class ProjectedAuthorizedFixTextEdit(
    val sourceId: String,
    val offset: Int,
    val length: Int,
    val replacement: String,
)

data class ProjectedAuthorizedFix(
    val title: String,
    val diagnosticCode: String,
    val edit: ProjectedAuthorizedFixTextEdit,
)

internal fun authorizedInsertClauseEdit(
    sourceText: String,
    anchorOffset: Int,
    compilerText: String,
): Pair<Int, String>? {
    if (compilerText.isEmpty() || anchorOffset < 0 || anchorOffset >= sourceText.length) return null
    val lineStart = sourceText.lastIndexOf('\n', anchorOffset) + 1
    val lineEnd = sourceText.indexOf('\n', anchorOffset)
    if (lineEnd < 0) return null
    val openBrace = sourceText.indexOf('{', anchorOffset)
    if (openBrace < 0 || openBrace >= lineEnd) return null
    val indentation = sourceText.substring(lineStart, lineEnd).takeWhile { it == ' ' || it == '\t' }
    return lineEnd + 1 to "$indentation  $compilerText\n"
}

/**
 * Bounded M10.5-04 projection of the Python `authorized_snapshot_fixes` contract.
 *
 * The planner consumes one exact source-text snapshot plus already-owned compiler diagnostics.
 * It never mutates source text. Only the established `insertClause` mapping is projected;
 * unsupported fix kinds and malformed anchors fail closed. Python remains the migration oracle.
 */
class ProjectAuthorizedFixPlanner private constructor(
    private val sourceById: Map<String, String>,
) {
    fun plan(
        sourceId: String,
        diagnostics: List<ProjectedAuthorizedFixDiagnostic>,
        diagnosticCodes: Set<String>? = null,
    ): List<ProjectedAuthorizedFix> {
        val sourceText = sourceById[sourceId] ?: return emptyList()
        val fixes = mutableListOf<ProjectedAuthorizedFix>()
        for (diagnostic in diagnostics) {
            if (diagnostic.sourceId != sourceId) continue
            if (diagnosticCodes != null && diagnostic.code !in diagnosticCodes) continue
            for (fix in diagnostic.allowedFixes) {
                if (fix.kind != "insertClause") continue
                val planned = authorizedInsertClauseEdit(sourceText, diagnostic.offset, fix.text) ?: continue
                fixes += ProjectedAuthorizedFix(
                    title = fix.text,
                    diagnosticCode = diagnostic.code,
                    edit = ProjectedAuthorizedFixTextEdit(
                        sourceId = sourceId,
                        offset = planned.first,
                        length = 0,
                        replacement = planned.second,
                    ),
                )
            }
        }
        return fixes
    }

    companion object {
        fun fromSources(sources: List<Pair<String, String>>): ProjectAuthorizedFixPlanner =
            ProjectAuthorizedFixPlanner(sources.toMap())
    }
}

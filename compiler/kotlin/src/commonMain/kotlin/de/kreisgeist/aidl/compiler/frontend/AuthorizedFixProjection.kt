package de.kreisgeist.aidl.compiler.frontend

data class ProjectedDiagnosticFix(
    val kind: String,
    val text: String,
)

data class ProjectedAuthorizedFixDiagnostic(
    val code: String,
    val sourceId: String,
    val offset: Int,
    val allowedFixes: List<ProjectedDiagnosticFix> = emptyList(),
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

/**
 * Bounded M10.5-04 projection of explicitly authorized diagnostic fixes.
 *
 * This query never applies edits and does not derive diagnostic meaning. The caller supplies the
 * exact compiler-owned diagnostic stream for the same source snapshot; this class only maps
 * existing `allowedFixes` entries onto conservative text edits. Unknown fix kinds and structurally
 * unplannable insertions are omitted rather than guessed.
 */
class ProjectAuthorizedFixQuery private constructor(
    private val sourceById: Map<String, String>,
    private val diagnostics: List<ProjectedAuthorizedFixDiagnostic>,
    private val validSnapshot: Boolean,
) {
    fun fixes(
        sourceId: String,
        diagnosticCodes: Set<String>? = null,
    ): List<ProjectedAuthorizedFix> {
        if (!validSnapshot) return emptyList()
        val text = sourceById[sourceId] ?: return emptyList()
        val fixes = mutableListOf<ProjectedAuthorizedFix>()
        for (diagnostic in diagnostics) {
            if (diagnostic.sourceId != sourceId) continue
            if (diagnosticCodes != null && diagnostic.code !in diagnosticCodes) continue
            for (fix in diagnostic.allowedFixes) {
                if (fix.kind != "insertClause") continue
                val planned = insertClauseEdit(text, diagnostic.offset, fix.text) ?: continue
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
        fun fromSnapshot(
            sources: List<Pair<String, String>>,
            diagnostics: List<ProjectedAuthorizedFixDiagnostic>,
        ): ProjectAuthorizedFixQuery {
            val sourceById = sources.toMap()
            val valid = sources.all { it.first.isNotBlank() } && sourceById.size == sources.size
            return ProjectAuthorizedFixQuery(sourceById, diagnostics.toList(), valid)
        }

        private fun insertClauseEdit(
            text: String,
            anchorOffset: Int,
            compilerText: String,
        ): Pair<Int, String>? {
            if (compilerText.isEmpty() || anchorOffset < 0 || anchorOffset >= text.length) return null
            val lineStart = text.lastIndexOf('\n', anchorOffset).let { if (it < 0) 0 else it + 1 }
            val lineEnd = text.indexOf('\n', anchorOffset)
            if (lineEnd < 0) return null
            val openBrace = text.indexOf('{', anchorOffset)
            if (openBrace < anchorOffset || openBrace >= lineEnd) return null
            val indentation = text.substring(lineStart, lineEnd).takeWhile { it == ' ' || it == '\t' }
            return lineEnd + 1 to "$indentation  $compilerText\n"
        }
    }
}

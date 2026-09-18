package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class AuthorizedFixPlanningCoverageTest {
    @Test
    fun insertClauseCoversIndentationAndEveryFailClosedAnchorBoundary() {
        val indented = "module x\n\tconsumer C {\n}\n"
        val anchor = indented.indexOf("consumer")
        assertEquals(
            indented.indexOf('\n', anchor) + 1 to "\t  clause\n",
            authorizedInsertClauseEdit(indented, anchor, "clause"),
        )
        assertNull(authorizedInsertClauseEdit(indented, anchor, ""))
        assertNull(authorizedInsertClauseEdit(indented, -1, "clause"))
        assertNull(authorizedInsertClauseEdit(indented, indented.length, "clause"))
        assertNull(authorizedInsertClauseEdit("consumer C {", 0, "clause"))
        assertNull(authorizedInsertClauseEdit("consumer C\n{}\n", 0, "clause"))
        assertNull(authorizedInsertClauseEdit("consumer C }\n{\n", 0, "clause"))
    }

    @Test
    fun multipleDiagnosticsAndFixesUseZeroLengthEditsAtTheSameStableInsertionPoint() {
        val source = "module x\nconsumer C {\n  call: downstream\n}\n"
        val offset = source.indexOf("consumer")
        val diagnostics = listOf(
            ProjectedAuthorizedFixDiagnostic(
                "A",
                "source",
                offset,
                listOf(
                    ProjectedAllowedDiagnosticFix("insertClause", "one"),
                    ProjectedAllowedDiagnosticFix("unsupported", "skip"),
                    ProjectedAllowedDiagnosticFix("insertClause", "two"),
                ),
            ),
            ProjectedAuthorizedFixDiagnostic(
                "B",
                "source",
                offset,
                listOf(ProjectedAllowedDiagnosticFix("insertClause", "three")),
            ),
        )
        val fixes = ProjectAuthorizedFixPlanner.fromSources(listOf("source" to source)).plan("source", diagnostics)
        assertEquals(listOf("one", "two", "three"), fixes.map { it.title })
        assertEquals(listOf(0, 0, 0), fixes.map { it.edit.length })
        assertEquals(1, fixes.map { it.edit.offset }.distinct().size)
    }
}

package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals

class AuthorizedFixDifferentialParityTest {
    private fun diagnostic(source: String) = ProjectedAuthorizedFixDiagnostic(
        code = "AIDL-DIST411",
        sourceId = "authorized-fixes.aidl",
        offset = source.indexOf("consumer"),
        allowedFixes = listOf(
            ProjectedDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
        ),
    )

    private fun render(label: String, fixes: List<ProjectedAuthorizedFix>): String {
        if (fixes.isEmpty()) return "$label|<none>"
        return fixes.joinToString("\n") { fix ->
            val edit = fix.edit
            val replacement = edit.replacement.replace("\n", "\\n")
            "$label|${fix.title}|${fix.diagnosticCode}|${edit.sourceId}:${edit.offset}:${edit.length}:$replacement"
        }
    }

    private fun matrix(): String {
        val source = File("parity/authorized-fixes.source").readText()
        val shifted = "\n$source"
        val saved = ProjectAuthorizedFixQuery.fromSnapshot(
            listOf("authorized-fixes.aidl" to source),
            listOf(diagnostic(source)),
        )
        val memory = ProjectAuthorizedFixQuery.fromSnapshot(
            listOf("authorized-fixes.aidl" to shifted),
            listOf(diagnostic(shifted)),
        )
        return listOf(
            render("saved-all", saved.fixes("authorized-fixes.aidl")),
            render("saved-filter-match", saved.fixes("authorized-fixes.aidl", setOf("AIDL-DIST411"))),
            render("saved-filter-empty", saved.fixes("authorized-fixes.aidl", emptySet())),
            render("saved-filter-miss", saved.fixes("authorized-fixes.aidl", setOf("AIDL-R001"))),
            render("memory-shifted", memory.fixes("authorized-fixes.aidl")),
        ).joinToString("\n")
    }

    @Test
    fun savedAndUnsavedMatrixMatchesPinnedPythonOracle() {
        assertEquals(File("parity/authorized-fixes.signature").readText().trimEnd(), matrix())
    }

    @Test
    fun repeatedProjectionIsDeterministic() {
        assertEquals(matrix(), matrix())
    }
}

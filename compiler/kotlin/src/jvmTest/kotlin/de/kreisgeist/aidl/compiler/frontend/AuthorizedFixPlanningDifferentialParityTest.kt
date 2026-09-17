package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals

class AuthorizedFixPlanningDifferentialParityTest {
    private val saved = "module parity.fix\nconsumer Worker {\n  call: downstream\n}\n"

    private fun diagnostic(sourceId: String, sourceText: String, fixes: List<ProjectedAllowedDiagnosticFix> = listOf(
        ProjectedAllowedDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
    )) = ProjectedAuthorizedFixDiagnostic(
        code = "AIDL-DIST411",
        sourceId = sourceId,
        offset = sourceText.indexOf("consumer"),
        allowedFixes = fixes,
    )

    private fun escape(value: String): String = value.replace("\\", "\\\\").replace("\n", "\\n")

    private fun render(label: String, fixes: List<ProjectedAuthorizedFix>): String =
        label + "|" + fixes.joinToString(";") {
            "${it.title}~${it.diagnosticCode}~${it.edit.sourceId}:${it.edit.offset}:${it.edit.length}:${escape(it.edit.replacement)}"
        }

    private fun matrix(): String {
        val unsaved = "\n$saved"
        val savedPlanner = ProjectAuthorizedFixPlanner.fromSources(listOf("fix" to saved))
        val unsavedPlanner = ProjectAuthorizedFixPlanner.fromSources(listOf("fix" to unsaved))
        val unsupported = diagnostic("fix", saved, listOf(ProjectedAllowedDiagnosticFix("replace", "ignored")))
        val multiple = diagnostic(
            "fix",
            saved,
            listOf(
                ProjectedAllowedDiagnosticFix("insertClause", "first"),
                ProjectedAllowedDiagnosticFix("insertClause", "second"),
            ),
        )
        val noBrace = saved.replace("consumer Worker {", "consumer Worker  ")
        val noLineTerminator = "module parity.fix\nconsumer Worker {"
        return listOf(
            render("saved", savedPlanner.plan("fix", listOf(diagnostic("fix", saved)))),
            render("filtered", savedPlanner.plan("fix", listOf(diagnostic("fix", saved)), setOf("OTHER"))),
            render("unsaved", unsavedPlanner.plan("fix", listOf(diagnostic("fix", unsaved)))),
            render("unsupported", savedPlanner.plan("fix", listOf(unsupported))),
            render("no-brace", ProjectAuthorizedFixPlanner.fromSources(listOf("fix" to noBrace)).plan("fix", listOf(diagnostic("fix", noBrace)))),
            render("no-line-terminator", ProjectAuthorizedFixPlanner.fromSources(listOf("fix" to noLineTerminator)).plan("fix", listOf(diagnostic("fix", noLineTerminator)))),
            render("multiple", savedPlanner.plan("fix", listOf(multiple))),
            render("missing-source", ProjectAuthorizedFixPlanner.fromSources(emptyList()).plan("fix", listOf(diagnostic("fix", saved)))),
        ).joinToString("\n")
    }

    @Test
    fun kotlinPlannerMatchesPinnedPythonAuthorizedFixOracle() {
        assertEquals(File("parity/authorized-fix-planning.signature").readText().trimEnd(), matrix())
    }

    @Test
    fun repeatedRunsAreDeterministic() {
        assertEquals(matrix(), matrix())
    }
}

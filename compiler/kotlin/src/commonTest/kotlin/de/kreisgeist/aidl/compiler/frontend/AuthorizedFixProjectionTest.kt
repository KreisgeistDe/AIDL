package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class AuthorizedFixProjectionTest {
    private val source = """module parity.fix
consumer Worker {
  start: workflow Flow
}
"""
    private fun diagnostic(
        text: String = source,
        code: String = "AIDL-DIST411",
        fixes: List<ProjectedDiagnosticFix> = listOf(
            ProjectedDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
        ),
    ) = ProjectedAuthorizedFixDiagnostic(code, "authorized-fixes.aidl", text.indexOf("consumer"), fixes)

    @Test
    fun projectsOnlyExplicitInsertClauseFixWithoutApplyingIt() {
        val query = ProjectAuthorizedFixQuery.fromSnapshot(
            listOf("authorized-fixes.aidl" to source),
            listOf(diagnostic()),
        )
        val result = query.fixes("authorized-fixes.aidl")
        assertEquals(1, result.size)
        assertEquals("idempotency: event.eventId retain 30d", result.single().title)
        assertEquals("AIDL-DIST411", result.single().diagnosticCode)
        assertEquals(36, result.single().edit.offset)
        assertEquals(0, result.single().edit.length)
        assertEquals("  idempotency: event.eventId retain 30d\n", result.single().edit.replacement)
        assertEquals(source, source)
    }

    @Test
    fun diagnosticCodeFilterMatchesPythonNoneEmptyAndMembershipSemantics() {
        val query = ProjectAuthorizedFixQuery.fromSnapshot(
            listOf("authorized-fixes.aidl" to source),
            listOf(diagnostic()),
        )
        assertEquals(1, query.fixes("authorized-fixes.aidl", null).size)
        assertEquals(1, query.fixes("authorized-fixes.aidl", setOf("AIDL-DIST411")).size)
        assertTrue(query.fixes("authorized-fixes.aidl", emptySet()).isEmpty())
        assertTrue(query.fixes("authorized-fixes.aidl", setOf("AIDL-R001")).isEmpty())
    }

    @Test
    fun unknownKindsAndStructurallyUnplannableInsertionsFailClosed() {
        val unsupported = diagnostic(
            fixes = listOf(
                ProjectedDiagnosticFix("replaceThing", "x"),
                ProjectedDiagnosticFix("insertClause", ""),
            ),
        )
        assertTrue(
            ProjectAuthorizedFixQuery.fromSnapshot(
                listOf("authorized-fixes.aidl" to source),
                listOf(unsupported),
            ).fixes("authorized-fixes.aidl").isEmpty(),
        )
        val noBrace = "consumer Worker\n"
        assertTrue(
            ProjectAuthorizedFixQuery.fromSnapshot(
                listOf("authorized-fixes.aidl" to noBrace),
                listOf(diagnostic(noBrace)),
            ).fixes("authorized-fixes.aidl").isEmpty(),
        )
        val noTrailingLine = "consumer Worker {"
        assertTrue(
            ProjectAuthorizedFixQuery.fromSnapshot(
                listOf("authorized-fixes.aidl" to noTrailingLine),
                listOf(diagnostic(noTrailingLine)),
            ).fixes("authorized-fixes.aidl").isEmpty(),
        )
    }

    @Test
    fun missingOrInvalidSnapshotFailsClosed() {
        val query = ProjectAuthorizedFixQuery.fromSnapshot(
            listOf("authorized-fixes.aidl" to source),
            listOf(diagnostic()),
        )
        assertTrue(query.fixes("missing.aidl").isEmpty())
        assertTrue(
            ProjectAuthorizedFixQuery.fromSnapshot(
                listOf("authorized-fixes.aidl" to source, "authorized-fixes.aidl" to source),
                listOf(diagnostic()),
            ).fixes("authorized-fixes.aidl").isEmpty(),
        )
        assertTrue(
            ProjectAuthorizedFixQuery.fromSnapshot(
                listOf("" to source),
                listOf(diagnostic()),
            ).fixes("").isEmpty(),
        )
    }

    @Test
    fun exactUnsavedSnapshotTextOwnsItsShiftedEditOffset() {
        val shifted = "\n$source"
        val query = ProjectAuthorizedFixQuery.fromSnapshot(
            listOf("authorized-fixes.aidl" to shifted),
            listOf(diagnostic(shifted)),
        )
        assertEquals(37, query.fixes("authorized-fixes.aidl").single().edit.offset)
    }

    @Test
    fun diagnosticAndAllowedFixOrderIncludingDuplicatesIsPreserved() {
        val first = diagnostic(
            code = "FIRST",
            fixes = listOf(
                ProjectedDiagnosticFix("insertClause", "one"),
                ProjectedDiagnosticFix("insertClause", "one"),
            ),
        )
        val second = diagnostic(
            code = "SECOND",
            fixes = listOf(ProjectedDiagnosticFix("insertClause", "two")),
        )
        val query = ProjectAuthorizedFixQuery.fromSnapshot(
            listOf("authorized-fixes.aidl" to source),
            listOf(first, second),
        )
        assertEquals(
            listOf("FIRST:one", "FIRST:one", "SECOND:two"),
            query.fixes("authorized-fixes.aidl").map { "${it.diagnosticCode}:${it.title}" },
        )
        assertEquals(query.fixes("authorized-fixes.aidl"), query.fixes("authorized-fixes.aidl"))
    }
}

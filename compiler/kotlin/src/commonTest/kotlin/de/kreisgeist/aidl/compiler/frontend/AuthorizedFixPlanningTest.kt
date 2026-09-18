package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class AuthorizedFixPlanningTest {
    private val source = "module parity.fix\nconsumer Worker {\n  call: downstream\n}\n"
    private val offset = source.indexOf("consumer")
    private val diagnostic = ProjectedAuthorizedFixDiagnostic(
        code = "AIDL-DIST411",
        sourceId = "fix",
        offset = offset,
        allowedFixes = listOf(
            ProjectedAllowedDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
        ),
    )

    @Test
    fun authorizedInsertClauseIsProjectedWithoutApplyingIt() {
        val planner = ProjectAuthorizedFixPlanner.fromSources(listOf("fix" to source))
        val fixes = planner.plan("fix", listOf(diagnostic))
        assertEquals(1, fixes.size)
        assertEquals("idempotency: event.eventId retain 30d", fixes.single().title)
        assertEquals("AIDL-DIST411", fixes.single().diagnosticCode)
        assertEquals("fix", fixes.single().edit.sourceId)
        assertEquals(source.indexOf('\n', offset) + 1, fixes.single().edit.offset)
        assertEquals(0, fixes.single().edit.length)
        assertEquals("  idempotency: event.eventId retain 30d\n", fixes.single().edit.replacement)
        assertTrue("idempotency" !in source)
    }

    @Test
    fun filteringUnsupportedKindsAndForeignSourcesFailClosed() {
        val planner = ProjectAuthorizedFixPlanner.fromSources(listOf("fix" to source))
        val unsupported = diagnostic.copy(
            allowedFixes = listOf(ProjectedAllowedDiagnosticFix("replace", "ignored")),
        )
        val foreign = diagnostic.copy(sourceId = "other")
        assertEquals(emptyList(), planner.plan("fix", listOf(diagnostic), emptySet()))
        assertEquals(emptyList(), planner.plan("fix", listOf(diagnostic), setOf("OTHER")))
        assertEquals(1, planner.plan("fix", listOf(diagnostic), setOf("AIDL-DIST411")).size)
        assertEquals(emptyList(), planner.plan("fix", listOf(unsupported, foreign)))
        assertEquals(emptyList(), planner.plan("missing", listOf(diagnostic)))
    }

    @Test
    fun diagnosticAndFixOrderingIsPreservedExactly() {
        val planner = ProjectAuthorizedFixPlanner.fromSources(listOf("fix" to source))
        val first = diagnostic.copy(
            code = "A",
            allowedFixes = listOf(
                ProjectedAllowedDiagnosticFix("insertClause", "first"),
                ProjectedAllowedDiagnosticFix("insertClause", "second"),
            ),
        )
        val second = diagnostic.copy(
            code = "B",
            allowedFixes = listOf(ProjectedAllowedDiagnosticFix("insertClause", "third")),
        )
        assertEquals(
            listOf("A:first", "A:second", "B:third"),
            planner.plan("fix", listOf(first, second)).map { "${it.diagnosticCode}:${it.title}" },
        )
    }

    @Test
    fun sourceSnapshotsRemainIsolatedAcrossRoots() {
        val rootA = ProjectAuthorizedFixPlanner.fromSources(listOf("root-a/fix" to source))
        val rootBSource = "  " + source
        val rootB = ProjectAuthorizedFixPlanner.fromSources(listOf("root-b/fix" to rootBSource))
        val a = diagnostic.copy(sourceId = "root-a/fix", offset = source.indexOf("consumer"))
        val b = diagnostic.copy(sourceId = "root-b/fix", offset = rootBSource.indexOf("consumer"))
        assertTrue(rootA.plan("root-a/fix", listOf(a)).all { it.edit.sourceId == "root-a/fix" })
        assertTrue(rootB.plan("root-b/fix", listOf(b)).all { it.edit.sourceId == "root-b/fix" })
        assertEquals(emptyList(), rootA.plan("root-a/fix", listOf(b)))
    }
}

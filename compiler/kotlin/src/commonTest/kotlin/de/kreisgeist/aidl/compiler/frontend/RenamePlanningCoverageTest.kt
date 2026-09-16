package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class RenamePlanningCoverageTest {
    private val provider = "module shared\nexport value Public {}\nexport value Other {}\n"
    private val consumer = "module consumer\nimport shared.Public\nentity Local { local: Local imported: Public missing: Missing }\n"
    private fun planner() = ProjectRenamePlanner.fromSources(listOf("consumer" to consumer, "provider" to provider))

    @Test
    fun sameSnapshotOverrideAndDeclarationTargetAreCovered() {
        val localDeclaration = consumer.indexOf("Local") + 1
        val saved = planner().plan("consumer", localDeclaration, "Renamed")
        val sameText = planner().plan("consumer", consumer, localDeclaration, "Renamed")
        assertEquals(saved, sameText)
        assertEquals(ProjectedRenameStatus.READY, saved.status)
        assertEquals("consumer.Renamed", saved.newFullyQualifiedName)
        assertEquals(listOf(consumer.indexOf("Local"), consumer.indexOf("Local", consumer.indexOf("local:"))), saved.edits.map { it.offset })
    }

    @Test
    fun malformedSourceSetsFailClosedWithoutThrowing() {
        val duplicate = ProjectRenamePlanner.fromSources(listOf("same" to consumer, "same" to provider))
        assertEquals(ProjectedRenameStatus.INVALID, duplicate.plan("same", 0, "Renamed").status)
        val blank = ProjectRenamePlanner.fromSources(listOf("" to consumer))
        assertEquals(ProjectedRenameStatus.INVALID, blank.plan("", 0, "Renamed").status)
        val lexical = ProjectRenamePlanner.fromSources(listOf("consumer" to "$consumer§"))
        assertEquals(ProjectedRenameStatus.INVALID, lexical.plan("consumer", 0, "Renamed").status)
    }

    @Test
    fun identifierValidationAcceptsPlainAndUnderscoreNamesAndRejectsReservedOrMalformed() {
        val imported = consumer.indexOf("Public", consumer.indexOf("imported:")) + 1
        assertEquals(ProjectedRenameStatus.READY, planner().plan("consumer", imported, "_Renamed2").status)
        for (name in listOf("", "entity", "2Renamed", "Renamed-name", "Public")) {
            assertTrue(planner().plan("consumer", imported, name).status in setOf(ProjectedRenameStatus.INVALID_NAME, ProjectedRenameStatus.READY))
        }
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner().plan("consumer", imported, "entity").status)
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner().plan("consumer", imported, "2Renamed").status)
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner().plan("consumer", imported, "Renamed-name").status)
    }

    @Test
    fun collisionUnresolvedUnknownSourceAndNonReferenceContextAreExplicit() {
        val imported = consumer.indexOf("Public", consumer.indexOf("imported:")) + 1
        assertEquals(ProjectedRenameStatus.COLLISION, planner().plan("consumer", imported, "Other").status)
        assertEquals(ProjectedRenameStatus.UNRESOLVED, planner().plan("consumer", consumer.indexOf("Missing") + 1, "Renamed").status)
        assertEquals(ProjectedRenameStatus.INVALID, planner().plan("unknown", 0, "Renamed").status)
        assertEquals(ProjectedRenameStatus.INVALID, planner().plan("consumer", consumer.indexOf("imported:") + "imported".length, "Renamed").status)
    }
}

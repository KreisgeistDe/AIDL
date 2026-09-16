package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class RenamePlanningTest {
    private val consumer = """module demo.consumer
import demo.shared.Public
import demo.shared.*
entity Local {}
entity Uses {
  local: Local
  imported: Public
  qualified: demo.shared.Public
  ambiguous: Duplicate
  missing: Missing
}
"""
    private val providerA = """module demo.shared
export value Public {}
value Hidden {}
export entity Duplicate {}
"""
    private val providerB = """module demo.shared
export enum Duplicate {}
export value Other {}
"""
    private fun sources() = listOf(
        "references-consumer" to consumer,
        "resolution-provider-a" to providerA,
        "resolution-provider-b" to providerB,
    )

    @Test
    fun readyPlanContainsDeclarationAndExactReferencesInStableOrder() {
        val offset = consumer.indexOf("Public\n", consumer.indexOf("imported:")) + 1
        val result = ProjectRenamePlanner.fromSources(sources()).plan("references-consumer", offset, "Renamed")
        assertEquals(ProjectedRenameStatus.READY, result.status)
        assertEquals("demo.shared.Public", result.target?.fullyQualifiedName)
        assertEquals("demo.shared.Renamed", result.newFullyQualifiedName)
        assertEquals(
            listOf(
                "references-consumer:40:6:Renamed",
                "references-consumer:125:6:Renamed",
                "references-consumer:157:6:Renamed",
                "resolution-provider-a:32:6:Renamed",
            ),
            result.edits.map { "${it.sourceId}:${it.offset}:${it.length}:${it.replacement}" },
        )
        assertTrue(result.edits.all { edit ->
            sources().toMap().getValue(edit.sourceId).substring(edit.offset, edit.offset + edit.length) == "Public"
        })
    }

    @Test
    fun unsavedSnapshotReprojectsAllRenameOffsets() {
        val shifted = "\n$consumer"
        val offset = shifted.indexOf("Public\n", shifted.indexOf("imported:")) + 1
        val result = ProjectRenamePlanner.fromSources(sources()).plan("references-consumer", shifted, offset, "Renamed")
        assertEquals(ProjectedRenameStatus.READY, result.status)
        assertEquals(listOf(41, 126, 158, 32), result.edits.map { it.offset })
        assertEquals(listOf("references-consumer", "references-consumer", "references-consumer", "resolution-provider-a"), result.edits.map { it.sourceId })
    }

    @Test
    fun invalidNamesUnresolvedAmbiguousAndCollisionMatchOracleStatuses() {
        val planner = ProjectRenamePlanner.fromSources(sources())
        val imported = consumer.indexOf("Public\n", consumer.indexOf("imported:")) + 1
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner.plan("references-consumer", imported, "").status)
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner.plan("references-consumer", imported, "entity").status)
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner.plan("references-consumer", imported, "1Bad").status)
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner.plan("references-consumer", imported, "Bad-Name").status)
        assertEquals(ProjectedRenameStatus.INVALID_NAME, planner.plan("references-consumer", imported, "Public").status)
        assertEquals(ProjectedRenameStatus.COLLISION, planner.plan("references-consumer", imported, "Other").status)
        assertEquals(ProjectedRenameStatus.AMBIGUOUS, planner.plan("references-consumer", consumer.indexOf("Duplicate") + 1, "Renamed").status)
        assertEquals(ProjectedRenameStatus.UNRESOLVED, planner.plan("references-consumer", consumer.indexOf("Missing") + 1, "Renamed").status)
    }

    @Test
    fun invalidSnapshotUnknownSourceAndInvalidOffsetFailClosed() {
        val broken = sources().map { (id, source) -> id to if (id == "references-consumer") "$source§" else source }
        assertEquals(ProjectedRenameStatus.INVALID, ProjectRenamePlanner.fromSources(broken).plan("references-consumer", 0, "Renamed").status)
        val planner = ProjectRenamePlanner.fromSources(sources())
        assertEquals(ProjectedRenameStatus.INVALID, planner.plan("missing", 0, "Renamed").status)
        assertEquals(ProjectedRenameStatus.INVALID, planner.plan("references-consumer", -1, "Renamed").status)
        assertEquals(ProjectedRenameStatus.INVALID, planner.plan("references-consumer", consumer.length, "Renamed").status)
        assertEquals(ProjectedRenameStatus.INVALID, planner.plan("references-consumer", "$consumer§", 0, "Renamed").status)
    }

    @Test
    fun repeatedAndSourceEnumerationOrderAreDeterministic() {
        val offset = consumer.indexOf("Public\n", consumer.indexOf("imported:")) + 1
        val first = ProjectRenamePlanner.fromSources(sources()).plan("references-consumer", offset, "Renamed")
        assertEquals(first, ProjectRenamePlanner.fromSources(sources()).plan("references-consumer", offset, "Renamed"))
        assertEquals(first, ProjectRenamePlanner.fromSources(sources().reversed()).plan("references-consumer", offset, "Renamed"))
    }

    @Test
    fun rootsRemainIsolated() {
        val sourceA = "module a\nentity A { ref: A }\n"
        val sourceB = "module b\nentity A { ref: A }\n"
        val resultA = ProjectRenamePlanner.fromSources(listOf("root-a" to sourceA)).plan("root-a", sourceA.lastIndexOf("A"), "Renamed")
        val resultB = ProjectRenamePlanner.fromSources(listOf("root-b" to sourceB)).plan("root-b", sourceB.lastIndexOf("A"), "Renamed")
        assertEquals("a.Renamed", resultA.newFullyQualifiedName)
        assertEquals("b.Renamed", resultB.newFullyQualifiedName)
        assertTrue(resultA.edits.all { it.sourceId == "root-a" })
        assertTrue(resultB.edits.all { it.sourceId == "root-b" })
    }
}

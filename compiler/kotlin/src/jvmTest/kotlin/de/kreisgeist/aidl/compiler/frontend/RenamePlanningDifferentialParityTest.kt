package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class RenamePlanningDifferentialParityTest {
    private fun sources(): List<Pair<String, String>> = listOf(
        "references-consumer" to File("parity/documentation-consumer.source").readText(),
        "resolution-provider-a" to File("parity/resolution-provider-a.source").readText(),
        "resolution-provider-b" to File("parity/resolution-provider-b.source").readText(),
    )

    private fun status(result: ProjectedRenameResult): String = when (result.status) {
        ProjectedRenameStatus.INVALID -> "invalid"
        ProjectedRenameStatus.INVALID_NAME -> "invalidName"
        ProjectedRenameStatus.UNRESOLVED -> "unresolved"
        ProjectedRenameStatus.AMBIGUOUS -> "ambiguous"
        ProjectedRenameStatus.COLLISION -> "collision"
        ProjectedRenameStatus.READY -> "ready"
    }

    private fun render(label: String, result: ProjectedRenameResult): String {
        val edits = result.edits.joinToString(",") { "${it.sourceId}:${it.offset}:${it.length}:${it.replacement}" }
        return listOf(
            label,
            status(result),
            result.target?.fullyQualifiedName.orEmpty(),
            result.newFullyQualifiedName.orEmpty(),
            edits,
        ).joinToString("|")
    }

    private fun matrix(entries: List<Pair<String, String>> = sources()): String {
        val sourceById = entries.toMap()
        val planner = ProjectRenamePlanner.fromSources(entries)
        val consumer = sourceById.getValue("references-consumer")
        val local = consumer.indexOf("Local\n", consumer.indexOf("local:")) + 1
        val imported = consumer.indexOf("Public\n", consumer.indexOf("imported:")) + 1
        val ambiguous = consumer.indexOf("Duplicate") + 1
        val shifted = "\n$consumer"
        val invalid = "$consumer§"
        return listOf(
            render("saved-local", planner.plan("references-consumer", local, "Renamed")),
            render("saved-imported", planner.plan("references-consumer", imported, "Renamed")),
            render("saved-ambiguous", planner.plan("references-consumer", ambiguous, "Renamed")),
            render("saved-collision", planner.plan("references-consumer", imported, "Other")),
            render("saved-invalid-name", planner.plan("references-consumer", imported, "entity")),
            render("memory-shifted-imported", planner.plan("references-consumer", shifted, shifted.indexOf("Public\n", shifted.indexOf("imported:")) + 1, "Renamed")),
            render("memory-lexical-failure", planner.plan("references-consumer", invalid, invalid.indexOf("Local\n", invalid.indexOf("local:")) + 1, "Renamed")),
        ).joinToString("\n")
    }

    @Test
    fun savedAndUnsavedMatrixMatchesPinnedPythonOracle() {
        assertEquals(File("parity/rename-planning.signature").readText().trimEnd(), matrix())
    }

    @Test
    fun repeatedAndReversedEnumerationAreDeterministic() {
        val first = matrix()
        assertEquals(first, matrix())
        assertEquals(first, matrix(sources().reversed()))
    }

    @Test
    fun isolatedRootPlansDoNotLeak() {
        val a = "module a\nentity A { ref: A }\n"
        val b = "module b\nentity A { ref: A }\n"
        val resultA = ProjectRenamePlanner.fromSources(listOf("root-a" to a)).plan("root-a", a.lastIndexOf("A"), "Renamed")
        val resultB = ProjectRenamePlanner.fromSources(listOf("root-b" to b)).plan("root-b", b.lastIndexOf("A"), "Renamed")
        assertEquals("a.Renamed", resultA.newFullyQualifiedName)
        assertEquals("b.Renamed", resultB.newFullyQualifiedName)
        assertTrue(resultA.edits.all { it.sourceId == "root-a" })
        assertTrue(resultB.edits.all { it.sourceId == "root-b" })
    }
}

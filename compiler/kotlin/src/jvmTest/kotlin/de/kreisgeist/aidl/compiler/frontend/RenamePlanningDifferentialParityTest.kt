package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class RenamePlanningDifferentialParityTest {
    private fun sources(): List<Pair<String, String>> = listOf(
        "rename-domain" to File("parity/canonical-ir-domain.source").readText(),
        "rename-ambiguity" to File("parity/rename-ambiguity.source").readText(),
        "rename-provider-one" to File("parity/rename-provider-one.source").readText(),
        "rename-provider-two" to File("parity/rename-provider-two.source").readText(),
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
        val domain = sourceById.getValue("rename-domain")
        val ambiguity = sourceById.getValue("rename-ambiguity")
        val planner = ProjectRenamePlanner.fromSources(entries)
        val statusOffset = domain.indexOf("Status") + 1
        val shifted = "\n$domain"
        val invalid = "$domain§"
        return listOf(
            render("saved-status", planner.plan("rename-domain", statusOffset, "Renamed")),
            render("saved-ambiguous", planner.plan("rename-ambiguity", ambiguity.indexOf("Shared") + 1, "Renamed")),
            render("saved-unresolved", planner.plan("rename-ambiguity", ambiguity.indexOf("Missing") + 1, "Renamed")),
            render("saved-collision", planner.plan("rename-domain", statusOffset, "Pet")),
            render("saved-invalid-name", planner.plan("rename-domain", statusOffset, "entity")),
            render(
                "memory-shifted-status",
                planner.plan("rename-domain", shifted, shifted.indexOf("Status") + 1, "Renamed"),
            ),
            render(
                "memory-lexical-failure",
                planner.plan("rename-domain", invalid, invalid.indexOf("Status") + 1, "Renamed"),
            ),
        ).joinToString("\n")
    }

    @Test
    fun savedAndUnsavedMatrixMatchesPinnedPythonOracle() {
        assertEquals(File("parity/rename-planning.signature").readText().trimEnd(), matrix())
    }

    @Test
    fun repeatedAndReversedSourceEnumerationAreDeterministic() {
        val first = matrix()
        assertEquals(first, matrix())
        assertEquals(first, matrix(sources().reversed()))
    }

    @Test
    fun isolatedRootPlansDoNotLeak() {
        val domain = File("parity/canonical-ir-domain.source").readText()
        val resultA = ProjectRenamePlanner.fromSources(listOf("root-a" to domain)).plan("root-a", domain.indexOf("Status") + 1, "Renamed")
        val resultB = ProjectRenamePlanner.fromSources(listOf("root-b" to domain)).plan("root-b", domain.indexOf("Status") + 1, "Renamed")
        assertEquals("parity.ir.domain.Renamed", resultA.newFullyQualifiedName)
        assertEquals("parity.ir.domain.Renamed", resultB.newFullyQualifiedName)
        assertTrue(resultA.edits.all { it.sourceId == "root-a" })
        assertTrue(resultB.edits.all { it.sourceId == "root-b" })
    }
}

package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals

class ReferencesQueryDifferentialParityTest {
    private fun sources(): List<Pair<String, String>> = listOf(
        "references-consumer" to File("parity/documentation-consumer.source").readText(),
        "resolution-provider-a" to File("parity/resolution-provider-a.source").readText(),
        "resolution-provider-b" to File("parity/resolution-provider-b.source").readText(),
    )

    private fun render(label: String, result: ProjectedReferencesResult): String {
        val usages = result.occurrences.joinToString(",") {
            "${it.sourceId}:${it.line}:${it.column}:${it.offset}:${it.length}"
        }
        return listOf(label, result.status.name.lowercase(), result.target?.fullyQualifiedName.orEmpty(), usages).joinToString("|")
    }

    private fun matrix(entries: List<Pair<String, String>> = sources()): String {
        val sourceById = entries.toMap()
        val query = ProjectReferencesQuery.fromSources(entries)
        val consumer = sourceById.getValue("references-consumer")
        val local = consumer.indexOf("Local\n", consumer.indexOf("local:")) + 1
        val imported = consumer.indexOf("Public\n", consumer.indexOf("imported:")) + 1
        val qualified = consumer.indexOf("demo.shared.Public", consumer.indexOf("qualified:")) + "demo.shared.".length + 1
        val ambiguous = consumer.indexOf("Duplicate") + 1
        val shifted = "\n$consumer"
        val invalid = "$consumer§"
        return listOf(
            render("saved-local", query.references("references-consumer", local)),
            render("saved-imported", query.references("references-consumer", imported)),
            render("saved-qualified", query.references("references-consumer", qualified)),
            render("saved-ambiguous", query.references("references-consumer", ambiguous)),
            render("memory-shifted-imported", query.references("references-consumer", shifted, shifted.indexOf("Public\n", shifted.indexOf("imported:")) + 1)),
            render("memory-lexical-failure", query.references("references-consumer", invalid, invalid.indexOf("Local\n", invalid.indexOf("local:")) + 1)),
        ).joinToString("\n")
    }

    @Test
    fun savedAndUnsavedMatrixMatchesPinnedPythonOracle() {
        assertEquals(File("parity/references-query.signature").readText().trimEnd(), matrix())
    }

    @Test
    fun repeatedAndReversedEnumerationAreDeterministic() {
        val first = matrix()
        assertEquals(first, matrix())
        assertEquals(first, matrix(sources().reversed()))
    }

    @Test
    fun isolatedRootQueriesDoNotLeak() {
        val a = "module a\nentity A { ref: A }\n"
        val b = "module b\nentity A { ref: A }\n"
        val resultA = ProjectReferencesQuery.fromSources(listOf("root-a" to a)).references("root-a", a.lastIndexOf("A"))
        val resultB = ProjectReferencesQuery.fromSources(listOf("root-b" to b)).references("root-b", b.lastIndexOf("A"))
        assertEquals(listOf("root-a"), resultA.occurrences.map { it.sourceId })
        assertEquals(listOf("root-b"), resultB.occurrences.map { it.sourceId })
    }
}

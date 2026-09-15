package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals

class DocumentationQueryDifferentialParityTest {
    private fun sources(): List<Pair<String, String>> =
        listOf("documentation-consumer", "resolution-provider-a", "resolution-provider-b").map { sourceId ->
            sourceId to File("parity/$sourceId.source").readText()
        }

    private fun render(label: String, result: ProjectedDocumentationResult): String {
        val declaration = result.declaration
        return listOf(
            label,
            result.status.name.lowercase(),
            declaration?.fullyQualifiedName.orEmpty(),
            declaration?.kind.orEmpty(),
            declaration?.sourceId.orEmpty(),
            declaration?.line?.toString().orEmpty(),
            declaration?.column?.toString().orEmpty(),
            declaration?.offset?.toString().orEmpty(),
            declaration?.representation.orEmpty(),
        ).joinToString("|")
    }

    private fun matrix(sourceEntries: List<Pair<String, String>> = sources()): String {
        val sourceById = sourceEntries.toMap()
        val query = ProjectDocumentationQuery.fromSources(sourceEntries)
        val consumer = sourceById.getValue("documentation-consumer")
        val local = consumer.indexOf("Local\n", consumer.indexOf("local:"))
        val imported = consumer.indexOf("Public\n", consumer.indexOf("imported:"))
        val qualified = consumer.indexOf("demo.shared.Public", consumer.indexOf("qualified:"))
        val ambiguous = consumer.indexOf("Duplicate\n")
        val missing = consumer.indexOf("Missing\n")
        val shifted = "\n$consumer"
        val invalid = "$consumer§"

        return listOf(
            render("saved-local", query.document("documentation-consumer", local + 1)),
            render("saved-imported", query.document("documentation-consumer", imported + 1)),
            render("saved-qualified", query.document("documentation-consumer", qualified + "demo.shared.".length + 1)),
            render("saved-ambiguous", query.document("documentation-consumer", ambiguous + 1)),
            render("saved-unresolved", query.document("documentation-consumer", missing + 1)),
            render("saved-invalid", query.document("documentation-consumer", consumer.length)),
            render(
                "memory-shifted-local",
                query.document(
                    "documentation-consumer",
                    shifted,
                    shifted.indexOf("Local\n", shifted.indexOf("local:")) + 1,
                ),
            ),
            render("memory-lexical-failure", query.document("documentation-consumer", invalid, 0)),
        ).joinToString("\n")
    }

    @Test
    fun savedAndInMemoryMatrixMatchesPinnedPythonOracleSignature() {
        assertEquals(
            File("parity/documentation-query.signature").readText().trimEnd(),
            matrix(),
        )
    }

    @Test
    fun documentationResultsAreDeterministicAcrossRepeatedQueries() {
        val first = matrix()
        val second = matrix()
        assertEquals(first, second)
    }

    @Test
    fun unknownSourceAndNonWordContextFailClosed() {
        val sourceEntries = sources()
        val query = ProjectDocumentationQuery.fromSources(sourceEntries)
        val consumer = sourceEntries.toMap().getValue("documentation-consumer")
        assertEquals(ProjectedDocumentationStatus.INVALID, query.document("missing-source", 0).status)
        assertEquals(ProjectedDocumentationStatus.INVALID, query.document("documentation-consumer", consumer.indexOf("local:") + 5).status)
        assertEquals(ProjectedDocumentationStatus.INVALID, query.document("missing-source", consumer, 0).status)
    }

    @Test
    fun identicalInMemoryTextUsesSameSavedResult() {
        val sourceEntries = sources()
        val query = ProjectDocumentationQuery.fromSources(sourceEntries)
        val consumer = sourceEntries.toMap().getValue("documentation-consumer")
        val offset = consumer.indexOf("Local\n", consumer.indexOf("local:")) + 1
        assertEquals(
            query.document("documentation-consumer", offset),
            query.document("documentation-consumer", consumer, offset),
        )
    }
}

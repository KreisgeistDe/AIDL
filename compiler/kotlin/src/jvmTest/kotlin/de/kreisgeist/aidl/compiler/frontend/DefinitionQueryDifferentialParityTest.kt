package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class DefinitionQueryDifferentialParityTest {
    private fun sources(): List<Pair<String, String>> =
        listOf("resolution-consumer", "resolution-provider-a", "resolution-provider-b").map { sourceId ->
            sourceId to File("parity/$sourceId.source").readText()
        }

    private fun render(label: String, result: ProjectedDefinitionResult): String {
        val target = result.target
        return listOf(
            label,
            result.status.name.lowercase(),
            result.reference.orEmpty(),
            target?.fullyQualifiedName.orEmpty(),
            target?.kind.orEmpty(),
            target?.sourceId.orEmpty(),
            target?.line?.toString().orEmpty(),
            target?.column?.toString().orEmpty(),
            target?.offset?.toString().orEmpty(),
        ).joinToString("|")
    }

    private fun matrix(sourceEntries: List<Pair<String, String>> = sources()): String {
        val sourceById = sourceEntries.toMap()
        val query = ProjectDefinitionQuery.fromSources(sourceEntries)
        val consumer = sourceById.getValue("resolution-consumer")
        val providerA = sourceById.getValue("resolution-provider-a")
        val providerB = sourceById.getValue("resolution-provider-b")
        val override = consumer +
            "entity Uses {\n" +
            "  hidden: Hidden\n" +
            "  missing: Missing\n" +
            "  duplicate: Duplicate\n" +
            "  imported: Public\n" +
            "}\n"

        return listOf(
            render("saved-local", query.definition("resolution-consumer", consumer.indexOf("Local"))),
            render("saved-exact-import", query.definition("resolution-consumer", consumer.indexOf("Public"))),
            render("saved-module-missing", query.definition("resolution-consumer", consumer.indexOf("demo.consumer"))),
            render("saved-hidden-local", query.definition("resolution-provider-a", providerA.indexOf("Hidden"))),
            render("saved-duplicate", query.definition("resolution-provider-a", providerA.indexOf("Duplicate"))),
            render("saved-other", query.definition("resolution-provider-b", providerB.indexOf("Other"))),
            render("saved-out-of-range", query.definition("resolution-consumer", consumer.length)),
            render("memory-hidden", query.definition("resolution-consumer", override, override.indexOf("Hidden", consumer.length))),
            render("memory-missing", query.definition("resolution-consumer", override, override.indexOf("Missing", consumer.length))),
            render("memory-duplicate", query.definition("resolution-consumer", override, override.indexOf("Duplicate", consumer.length))),
            render("memory-public", query.definition("resolution-consumer", override, override.indexOf("Public", consumer.length))),
            render("memory-lexical-failure", query.definition("resolution-consumer", "$consumer§", 0)),
        ).joinToString("\n")
    }

    @Test
    fun savedAndInMemoryMatrixMatchesPinnedPythonOracleSignature() {
        assertEquals(
            File("parity/definition-query.signature").readText().trimEnd(),
            matrix(),
        )
    }

    @Test
    fun definitionIsDeterministicAcrossRepeatedAndSourceOrderRuns() {
        val forward = matrix()
        repeat(4) {
            assertEquals(forward, matrix())
        }
        assertEquals(forward, matrix(sources().reversed()))
    }

    @Test
    fun failClosedAndAmbiguityBoundariesAreExplicit() {
        val sourceEntries = sources()
        val query = ProjectDefinitionQuery.fromSources(sourceEntries)
        val consumer = sourceEntries.toMap().getValue("resolution-consumer")
        val invalidUnknownSource = query.definition("missing-source", 0)
        val invalidNegative = query.definition("resolution-consumer", -1)
        val invalidWhitespace = query.definition("resolution-consumer", consumer.indexOf(" "))
        val ambiguous = query.definition(
            "resolution-provider-a",
            sourceEntries.toMap().getValue("resolution-provider-a").indexOf("Duplicate"),
        )

        assertEquals(ProjectedDefinitionStatus.INVALID, invalidUnknownSource.status)
        assertEquals(ProjectedDefinitionStatus.INVALID, invalidNegative.status)
        assertEquals(ProjectedDefinitionStatus.INVALID, invalidWhitespace.status)
        assertEquals(ProjectedDefinitionStatus.AMBIGUOUS, ambiguous.status)
        assertNull(ambiguous.target)

        val resolver = ProjectNameResolver.fromSources(sourceEntries)
        assertEquals(2, resolver.resolve("resolution-provider-a", "Duplicate").symbols.size)
    }
}

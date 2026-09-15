package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals

class CompletionQueryDifferentialParityTest {
    private fun sources(): List<Pair<String, String>> =
        listOf("completion-consumer", "resolution-provider-a", "resolution-provider-b").map { sourceId ->
            sourceId to File("parity/$sourceId.source").readText()
        }

    private fun render(label: String, result: ProjectedCompletionResult): String {
        val candidates = result.candidates.joinToString(";") { candidate ->
            listOf(
                candidate.insertText,
                candidate.displayText,
                candidate.fullyQualifiedName,
                candidate.kind,
                candidate.origin,
                candidate.sourceId,
                candidate.sourceOffset.toString(),
            ).joinToString("~")
        }
        return listOf(
            label,
            result.status.name.lowercase(),
            result.prefix.orEmpty(),
            result.qualifier.orEmpty(),
            candidates,
        ).joinToString("|")
    }

    private fun matrix(sourceEntries: List<Pair<String, String>> = sources()): String {
        val sourceById = sourceEntries.toMap()
        val query = ProjectCompletionQuery.fromSources(sourceEntries)
        val consumer = sourceById.getValue("completion-consumer")
        val qualified = consumer.indexOf("demo.shared.Pub", startIndex = 80)
        val local = consumer.indexOf("Loc\n")
        val exact = consumer.indexOf("Pub\n")
        val ambiguous = consumer.indexOf("Dup\n")
        val shifted = "\n$consumer"
        val invalid = "$consumer§"

        return listOf(
            render("saved-local", query.complete("completion-consumer", local + 3)),
            render("saved-exact", query.complete("completion-consumer", exact + 3)),
            render(
                "saved-qualified",
                query.complete("completion-consumer", qualified + "demo.shared.Pub".length),
            ),
            render(
                "saved-dot",
                query.complete("completion-consumer", qualified + "demo.shared.".length),
            ),
            render("saved-ambiguous", query.complete("completion-consumer", ambiguous + 3)),
            render(
                "saved-invalid-key",
                query.complete("completion-consumer", consumer.indexOf("local:") + 3),
            ),
            render(
                "saved-invalid-module",
                query.complete("completion-consumer", consumer.indexOf("demo.consumer") + 4),
            ),
            render("saved-out-of-range", query.complete("completion-consumer", consumer.length + 1)),
            render(
                "memory-shifted-local",
                query.complete("completion-consumer", shifted, shifted.indexOf("Loc\n") + 3),
            ),
            render("memory-lexical-failure", query.complete("completion-consumer", invalid, 0)),
        ).joinToString("\n")
    }

    @Test
    fun savedAndInMemoryMatrixMatchesPinnedPythonOracleSignature() {
        assertEquals(
            File("parity/completion-query.signature").readText().trimEnd(),
            matrix(),
        )
    }

    @Test
    fun completionIsDeterministicAcrossRepeatedAndSourceOrderRuns() {
        val forward = matrix()
        repeat(4) {
            assertEquals(forward, matrix())
        }
        assertEquals(forward, matrix(sources().reversed()))
    }

    @Test
    fun failClosedContextAndAmbiguityBoundariesAreExplicit() {
        val sourceEntries = sources()
        val query = ProjectCompletionQuery.fromSources(sourceEntries)
        val consumer = sourceEntries.toMap().getValue("completion-consumer")

        assertEquals(ProjectedCompletionStatus.INVALID, query.complete("missing-source", 0).status)
        assertEquals(
            ProjectedCompletionStatus.INVALID,
            query.complete("missing-source", consumer, 0).status,
        )
        assertEquals(ProjectedCompletionStatus.INVALID, query.complete("completion-consumer", -1).status)
        assertEquals(
            ProjectedCompletionStatus.INVALID,
            query.complete("completion-consumer", consumer.indexOf("entity Uses") + 8).status,
        )

        val ambiguous = query.complete("completion-consumer", consumer.indexOf("Dup\n") + 3)
        assertEquals(ProjectedCompletionStatus.RESOLVED, ambiguous.status)
        assertEquals("Dup", ambiguous.prefix)
        assertEquals(emptyList(), ambiguous.candidates)
    }
}

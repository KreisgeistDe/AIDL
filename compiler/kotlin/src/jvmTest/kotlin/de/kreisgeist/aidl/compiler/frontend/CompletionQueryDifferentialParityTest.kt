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
        assertEquals(ProjectedCompletionStatus.INVALID, query.complete("completion-consumer", consumer.length).status)
        assertEquals(
            ProjectedCompletionStatus.INVALID,
            query.complete("completion-consumer", consumer.indexOf("entity Uses")).status,
        )
        assertEquals(
            ProjectedCompletionStatus.INVALID,
            query.complete("completion-consumer", consumer.indexOf("local:") + "local:".length).status,
        )

        val leadingSourceEntries = sourceEntries.map { (sourceId, source) ->
            sourceId to if (sourceId == "completion-consumer") "\n$source" else source
        }
        assertEquals(
            ProjectedCompletionStatus.INVALID,
            ProjectCompletionQuery.fromSources(leadingSourceEntries).complete("completion-consumer", 0).status,
        )

        val ambiguous = query.complete("completion-consumer", consumer.indexOf("Dup\n") + 3)
        assertEquals(ProjectedCompletionStatus.RESOLVED, ambiguous.status)
        assertEquals("Dup", ambiguous.prefix)
        assertEquals(emptyList(), ambiguous.candidates)
    }

    @Test
    fun nonReferenceClauseValueTokensMatchPythonFailClosedBoundary() {
        val source = """module demo
entity Local {}
entity Uses {
  stringValue: "Local"
  numberValue: 123
  annotationValue: @Local
}
"""
        val query = ProjectCompletionQuery.fromSources(listOf("non-reference" to source))
        val offsets = listOf(
            source.indexOf("\"Local\"") + 3,
            source.indexOf("123") + 2,
            source.indexOf("@Local") + 3,
        )

        for (offset in offsets) {
            val result = query.complete("non-reference", offset)
            assertEquals(ProjectedCompletionStatus.INVALID, result.status)
            assertEquals(null, result.prefix)
            assertEquals(null, result.qualifier)
            assertEquals(emptyList(), result.candidates)
        }
    }

    @Test
    fun prefixWildcardModulelessAndOverrideBranchesStayBounded() {
        val providerA = File("parity/resolution-provider-a.source").readText()
        val providerB = File("parity/resolution-provider-b.source").readText()
        val moduleless = "entity Local {}\nentity Uses { target: Local }\n"
        val consumer = """module demo.consumer
import demo.shared.*
entity Local {}
entity _Local {}
entity Uses {
  partial: Local
  underscore: _Lo
  wildcard: Other
  none: Zzz
  nested: demo.
}
"""
        val sourceEntries = listOf(
            "inline-consumer" to consumer,
            "resolution-provider-a" to providerA,
            "resolution-provider-b" to providerB,
            "moduleless" to moduleless,
        )
        val query = ProjectCompletionQuery.fromSources(sourceEntries)

        val partialStart = consumer.indexOf("Local\n", startIndex = 80)
        val partial = query.complete("inline-consumer", partialStart + 3)
        assertEquals(ProjectedCompletionStatus.RESOLVED, partial.status)
        assertEquals("Loc", partial.prefix)
        assertEquals(listOf("Local"), partial.candidates.map { it.insertText })
        assertEquals(
            partial,
            query.complete("inline-consumer", consumer, partialStart + 3),
        )

        val underscoreStart = consumer.indexOf("_Lo\n")
        val underscore = query.complete("inline-consumer", underscoreStart + 3)
        assertEquals("_Lo", underscore.prefix)
        assertEquals(listOf("_Local"), underscore.candidates.map { it.insertText })

        val wildcardStart = consumer.indexOf("Other\n")
        val wildcard = query.complete("inline-consumer", wildcardStart + 3)
        assertEquals(listOf("Other"), wildcard.candidates.map { it.insertText })
        assertEquals("wildcardImport:demo.shared.*", wildcard.candidates.single().origin)

        val none = query.complete("inline-consumer", consumer.indexOf("Zzz\n") + 3)
        assertEquals(ProjectedCompletionStatus.RESOLVED, none.status)
        assertEquals(emptyList(), none.candidates)

        val nestedDot = query.complete("inline-consumer", consumer.indexOf("demo.\n") + "demo.".length)
        assertEquals(ProjectedCompletionStatus.RESOLVED, nestedDot.status)
        assertEquals("demo", nestedDot.qualifier)
        assertEquals(emptyList(), nestedDot.candidates)

        val modulelessResult = query.complete(
            "moduleless",
            moduleless.lastIndexOf("Local") + 3,
        )
        assertEquals(ProjectedCompletionStatus.RESOLVED, modulelessResult.status)
        assertEquals(emptyList(), modulelessResult.candidates)

        val providerOverride = providerA + "entity Probe { target: Pub }\n"
        val providerResult = ProjectCompletionQuery.fromSources(sources()).complete(
            "resolution-provider-a",
            providerOverride,
            providerOverride.lastIndexOf("Pub") + 3,
        )
        assertEquals(listOf("Public"), providerResult.candidates.map { it.insertText })
        assertEquals("local:demo.shared", providerResult.candidates.single().origin)

        val malformedQualifier = "module demo\nentity Local {}\nentity Uses { target: . }\n"
        val malformedQuery = ProjectCompletionQuery.fromSources(listOf("malformed" to malformedQualifier))
        assertEquals(
            ProjectedCompletionStatus.INVALID,
            malformedQuery.complete("malformed", malformedQualifier.indexOf(". }") + 1).status,
        )

        val leadingDotQualifier = "module demo\nentity Local {}\nentity Uses { target: .demo. }\n"
        val leadingDotQuery = ProjectCompletionQuery.fromSources(listOf("leading-dot" to leadingDotQualifier))
        assertEquals(
            ProjectedCompletionStatus.INVALID,
            leadingDotQuery.complete(
                "leading-dot",
                leadingDotQualifier.indexOf(".demo.") + ".demo.".length,
            ).status,
        )
    }
}

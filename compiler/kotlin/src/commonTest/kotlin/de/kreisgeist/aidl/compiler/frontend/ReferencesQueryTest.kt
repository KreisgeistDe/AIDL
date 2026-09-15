package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ReferencesQueryTest {
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
    fun localImportedAndQualifiedReferencesUseExactSemanticIdentity() {
        val query = ProjectReferencesQuery.fromSources(sources())
        val local = query.references("references-consumer", consumer.indexOf("Local\n", consumer.indexOf("local:")) + 1)
        assertEquals(ProjectedReferencesStatus.RESOLVED, local.status)
        assertEquals("demo.consumer.Local", local.target?.fullyQualifiedName)
        assertEquals(listOf(107), local.occurrences.map { it.offset })

        val public = query.references("references-consumer", consumer.indexOf("Public\n", consumer.indexOf("imported:")) + 1)
        assertEquals(ProjectedReferencesStatus.RESOLVED, public.status)
        assertEquals("demo.shared.Public", public.target?.fullyQualifiedName)
        assertEquals(listOf(40, 125, 157), public.occurrences.map { it.offset })
        assertTrue(public.occurrences.all { it.sourceId == "references-consumer" })
    }

    @Test
    fun ambiguityInvalidOffsetsUnknownSourcesAndLexicalFailureFailClosed() {
        val query = ProjectReferencesQuery.fromSources(sources())
        assertEquals(
            ProjectedReferencesStatus.AMBIGUOUS,
            query.references("references-consumer", consumer.indexOf("Duplicate") + 1).status,
        )
        assertEquals(ProjectedReferencesStatus.INVALID, query.references("references-consumer", consumer.length).status)
        assertEquals(ProjectedReferencesStatus.INVALID, query.references("missing", 0).status)
        assertEquals(
            ProjectedReferencesStatus.INVALID,
            query.references("references-consumer", "$consumer§", 0).status,
        )
    }

    @Test
    fun inMemoryShiftIsTransientAndDeterministic() {
        val query = ProjectReferencesQuery.fromSources(sources())
        val shifted = "\n$consumer"
        val offset = shifted.indexOf("Public\n", shifted.indexOf("imported:")) + 1
        val first = query.references("references-consumer", shifted, offset)
        val second = query.references("references-consumer", shifted, offset)
        assertEquals(first, second)
        assertEquals(listOf(41, 126, 158), first.occurrences.map { it.offset })
        assertEquals(listOf(2, 8, 9), first.occurrences.map { it.line })
    }

    @Test
    fun sourceEnumerationOrderDoesNotChangeOccurrences() {
        val forward = ProjectReferencesQuery.fromSources(sources())
        val reversed = ProjectReferencesQuery.fromSources(sources().reversed())
        val offset = consumer.indexOf("Public\n", consumer.indexOf("imported:")) + 1
        assertEquals(
            forward.references("references-consumer", offset).occurrences,
            reversed.references("references-consumer", offset).occurrences,
        )
    }

    @Test
    fun isolatedRootsCannotLeakReferenceOccurrences() {
        val rootA = ProjectReferencesQuery.fromSources(listOf("root-a" to "module a\nentity A { ref: A }\n"))
        val rootB = ProjectReferencesQuery.fromSources(listOf("root-b" to "module b\nentity A { ref: A }\n"))
        val sourceA = "module a\nentity A { ref: A }\n"
        val sourceB = "module b\nentity A { ref: A }\n"
        val resultA = rootA.references("root-a", sourceA.lastIndexOf("A") )
        val resultB = rootB.references("root-b", sourceB.lastIndexOf("A") )
        assertEquals(listOf("root-a"), resultA.occurrences.map { it.sourceId })
        assertEquals(listOf("root-b"), resultB.occurrences.map { it.sourceId })
        assertEquals("a.A", resultA.target?.fullyQualifiedName)
        assertEquals("b.A", resultB.target?.fullyQualifiedName)
    }
}

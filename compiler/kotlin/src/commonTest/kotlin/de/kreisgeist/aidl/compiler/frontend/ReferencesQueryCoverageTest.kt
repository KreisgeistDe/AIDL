package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ReferencesQueryCoverageTest {
    private val provider = "module shared\nexport value Public {}\n"
    private val consumer = "module consumer\nimport shared.Public\nentity Local { local: Local imported: Public missing: Missing qualified: shared.Public }\n"
    private fun query() = ProjectReferencesQuery.fromSources(listOf("consumer" to consumer, "provider" to provider))

    @Test
    fun unresolvedAndSameTextBranchesAreExplicit() {
        val query = query()
        val missing = consumer.indexOf("Missing") + 1
        assertEquals(ProjectedReferencesStatus.UNRESOLVED, query.references("consumer", missing).status)
        val local = consumer.indexOf("Local", consumer.indexOf("local:")) + 1
        assertEquals(query.references("consumer", local), query.references("consumer", consumer, local))
        assertEquals(ProjectedReferencesStatus.INVALID, query.references("unknown", consumer, local).status)
    }

    @Test
    fun terminalProjectionUsesOnlyQualifiedTerminalWords() {
        val terminals = AidlSourceProjector.terminalReferences(consumer)
        val qualified = terminals.filter { it.reference == "shared.Public" }
        assertTrue(qualified.isNotEmpty())
        assertTrue(qualified.all { it.terminal == "Public" && it.length == 6 })
        assertTrue(terminals.none { it.reference == "shared" && it.offset == consumer.lastIndexOf("shared.Public") })
    }

    @Test
    fun declarationQueryExcludesDeclarationButRetainsBodyReference() {
        val query = query()
        val declaration = consumer.indexOf("Local") + 1
        val result = query.references("consumer", declaration)
        assertEquals(ProjectedReferencesStatus.RESOLVED, result.status)
        assertEquals("consumer.Local", result.target?.fullyQualifiedName)
        assertEquals(1, result.occurrences.size)
        assertEquals(consumer.indexOf("Local", consumer.indexOf("local:")), result.occurrences.single().offset)
    }

    @Test
    fun invalidLexicalOverrideAndInvalidContextRemainEmpty() {
        val query = query()
        assertEquals(ProjectedReferencesStatus.INVALID, query.references("consumer", "$consumer§", 0).status)
        assertEquals(ProjectedReferencesStatus.INVALID, query.references("consumer", consumer.indexOf("local:") + 5).status)
    }
}

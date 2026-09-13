package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class NameResolutionCoverageTest {
    @Test
    fun unresolvedExplicitAndWildcardImportsStayEmpty() {
        val project = ProjectNameResolver.fromSources(
            listOf(
                "consumer" to """
                    module demo.consumer
                    import missing.Type
                    import absent.module.*
                    entity Local {}
                """.trimIndent(),
                "provider" to "module demo.shared\nexport value Visible {}",
            ),
        )
        assertEquals(2, project.importResolutions.size)
        assertTrue(project.importResolutions.all { it.symbols.isEmpty() })
        assertEquals(ProjectedResolutionStatus.UNRESOLVED, project.resolve("consumer", "Type").status)
    }

    @Test
    fun exportedUnscopedDeclarationDoesNotEnterImportIndexes() {
        val project = ProjectNameResolver.fromSources(
            listOf(
                "loose" to "export value Loose {}",
                "consumer" to "module demo.consumer\nimport Loose\nimport missing.*\n",
            ),
        )
        val loose = project.symbols.first()
        assertTrue(loose.exported)
        assertNull(loose.module)
        assertNull(loose.fullyQualifiedName)
        assertTrue(project.importResolutions.all { it.symbols.isEmpty() })
    }

    @Test
    fun emptyProjectAndEmptyModuleDocumentRemainDeterministic() {
        val empty = ProjectNameResolver.fromSources(emptyList())
        assertEquals(emptyList(), empty.documents)
        assertEquals(emptyList(), empty.symbols)
        assertEquals(emptyList(), empty.importResolutions)

        val moduleOnly = ProjectNameResolver.fromSources(listOf("module-only" to "module demo.empty"))
        assertEquals("demo.empty", moduleOnly.documents.single().projection.module)
        assertTrue(moduleOnly.symbols.isEmpty())
        assertTrue(moduleOnly.importResolutions.isEmpty())
    }
}

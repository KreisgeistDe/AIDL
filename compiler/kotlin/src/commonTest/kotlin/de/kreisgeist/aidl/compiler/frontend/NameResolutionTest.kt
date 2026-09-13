package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull

class NameResolutionTest {
    private fun resolver(): ProjectNameResolver = ProjectNameResolver.fromSources(
        listOf(
            "consumer" to """
                module demo.consumer
                import demo.shared.Public
                import demo.shared.*
                entity Local {}
            """.trimIndent(),
            "provider-a" to """
                module demo.shared
                export value Public {}
                value Hidden {}
                export entity Duplicate {}
            """.trimIndent(),
            "provider-b" to """
                module demo.shared
                export enum Duplicate {}
                export value Other {}
            """.trimIndent(),
        ),
    )

    @Test
    fun derivesFqnsAndStableIdentitiesInProjectOrder() {
        val symbols = resolver().symbols
        assertEquals(
            listOf(
                "demo.consumer.Local@consumer#0",
                "demo.shared.Public@provider-a#0",
                "demo.shared.Hidden@provider-a#1",
                "demo.shared.Duplicate@provider-a#2",
                "demo.shared.Duplicate@provider-b#0",
                "demo.shared.Other@provider-b#1",
            ),
            symbols.map { it.stableIdentity },
        )
    }

    @Test
    fun preservesUnscopedDeclarationsWithoutInventingFqn() {
        val project = ProjectNameResolver.fromSources(listOf("unscoped" to "entity Loose {}"))
        assertNull(project.symbols.single().fullyQualifiedName)
        assertNull(project.symbols.single().stableIdentity)
        assertEquals(ProjectedResolutionStatus.UNRESOLVED, project.resolve("unscoped", "Loose").status)
    }

    @Test
    fun resolvesExplicitAndWildcardImportsUsingExportsOnly() {
        val project = resolver()
        assertEquals(
            listOf("demo.shared.Public@provider-a#0"),
            project.importResolutions[0].symbols.map { it.stableIdentity },
        )
        assertEquals(
            listOf(
                "demo.shared.Public@provider-a#0",
                "demo.shared.Duplicate@provider-a#2",
                "demo.shared.Duplicate@provider-b#0",
                "demo.shared.Other@provider-b#1",
            ),
            project.importResolutions[1].symbols.map { it.stableIdentity },
        )
    }

    @Test
    fun resolvesLocalImportedQualifiedAndAmbiguousNames() {
        val project = resolver()
        assertEquals(ProjectedResolutionStatus.RESOLVED, project.resolve("consumer", "Local").status)
        assertEquals(ProjectedResolutionStatus.RESOLVED, project.resolve("consumer", "Public").status)
        assertEquals(ProjectedResolutionStatus.UNRESOLVED, project.resolve("consumer", "Hidden").status)
        assertEquals(ProjectedResolutionStatus.RESOLVED, project.resolve("consumer", "demo.shared.Hidden").status)
        val duplicate = project.resolve("consumer", "Duplicate")
        assertEquals(ProjectedResolutionStatus.AMBIGUOUS, duplicate.status)
        assertEquals(
            listOf("demo.shared.Duplicate@provider-a#2", "demo.shared.Duplicate@provider-b#0"),
            duplicate.symbols.map { it.stableIdentity },
        )
    }

    @Test
    fun deduplicatesSameSymbolReachedByExplicitAndWildcardImport() {
        val resolution = resolver().resolve("consumer", "Public")
        assertEquals(1, resolution.symbols.size)
        assertEquals("demo.shared.Public@provider-a#0", resolution.symbols.single().stableIdentity)
    }

    @Test
    fun preservesDuplicateFqnLookupOrder() {
        assertEquals(
            listOf("provider-a", "provider-b"),
            resolver().lookupFullyQualified("demo.shared.Duplicate").map { it.sourceId },
        )
        assertEquals(emptyList(), resolver().lookupFullyQualified("demo.shared.Missing"))
    }

    @Test
    fun failsClosedForInvalidResolverInputs() {
        assertFailsWith<IllegalArgumentException> {
            ProjectNameResolver.fromSources(listOf("same" to "module a", "same" to "module b"))
        }
        assertFailsWith<IllegalArgumentException> {
            ProjectNameResolver.fromSources(listOf("" to "module a"))
        }
        val project = resolver()
        assertFailsWith<IllegalArgumentException> { project.resolve("missing", "Public") }
        assertFailsWith<IllegalArgumentException> { project.resolve("consumer", "") }
    }
}

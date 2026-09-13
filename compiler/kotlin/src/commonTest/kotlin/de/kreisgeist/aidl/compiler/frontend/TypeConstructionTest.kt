package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class TypeConstructionTest {
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
                export entity Duplicate {}
            """.trimIndent(),
            "provider-b" to """
                module demo.shared
                export enum Duplicate {}
            """.trimIndent(),
        ),
    )

    @Test
    fun constructsFrozenScalarListOptionalAndRangeShapes() {
        val scalar = ProjectedTypeConstructor.construct("string")
        assertEquals("string", scalar.stableSignature())
        assertFalse(scalar.isList)

        val list = ProjectedTypeConstructor.construct("[uuid]?")
        assertEquals("[uuid]?", list.stableSignature())
        assertTrue(list.isList)

        val ranged = ProjectedTypeConstructor.construct("string(1..80)?")
        assertEquals("string", ranged.name)
        assertTrue(ranged.nullable)
        assertEquals(ProjectedTypeRange("1", "80"), ranged.range)
        assertEquals("string(1..80)?", ranged.stableSignature())

        val signedDecimalRange = ProjectedTypeConstructor.construct("decimal(-1.5..2.25)")
        assertEquals(ProjectedTypeRange("-1.5", "2.25"), signedDecimalRange.range)
    }

    @Test
    fun enforcesProjectedTypeShapeInvariants() {
        assertFailsWith<IllegalArgumentException> { ProjectedTypeRef() }
        assertFailsWith<IllegalArgumentException> {
            ProjectedTypeRef(name = "string", elementType = ProjectedTypeRef(name = "uuid"))
        }
        assertFailsWith<IllegalArgumentException> {
            ProjectedTypeRef(
                elementType = ProjectedTypeRef(name = "uuid"),
                range = ProjectedTypeRange("1", "2"),
            )
        }
    }

    @Test
    fun checksBuiltinsLocalImportedQualifiedAndAmbiguousNames() {
        val project = resolver()
        assertEquals(ProjectedTypeResolutionStatus.RESOLVED, ProjectedTypeConstructor.check("consumer", "uuid", project).status)
        assertEquals(ProjectedTypeResolutionStatus.RESOLVED, ProjectedTypeConstructor.check("consumer", "Local", project).status)
        val imported = ProjectedTypeConstructor.check("consumer", "Public", project)
        assertEquals(ProjectedTypeResolutionStatus.RESOLVED, imported.status)
        assertEquals(listOf("demo.shared.Public@provider-a#0"), imported.symbols.map { it.stableIdentity })
        assertEquals(
            ProjectedTypeResolutionStatus.RESOLVED,
            ProjectedTypeConstructor.check("consumer", "demo.shared.Public", project).status,
        )
        assertEquals(ProjectedTypeResolutionStatus.AMBIGUOUS, ProjectedTypeConstructor.check("consumer", "Duplicate", project).status)
        assertEquals(ProjectedTypeResolutionStatus.UNRESOLVED, ProjectedTypeConstructor.check("consumer", "Missing", project).status)
    }

    @Test
    fun checksNestedListElementWithoutInventingContainerSymbols() {
        val check = ProjectedTypeConstructor.check("consumer", "[Public]?", resolver())
        assertEquals(ProjectedTypeResolutionStatus.RESOLVED, check.status)
        assertEquals("[Public]?", check.type.stableSignature())
        assertEquals(listOf("demo.shared.Public@provider-a#0"), check.symbols.map { it.stableIdentity })
    }

    @Test
    fun materializesDeterministicTypeFactsOnly() {
        val materialized = ProjectedTypeConstructor.materialize(
            ProjectedTypeConstructor.check("consumer", "Public?", resolver()),
        )
        assertEquals("Public?", materialized.signature)
        assertTrue(materialized.nullable)
        assertEquals("Public", materialized.baseName)
        assertNull(materialized.elementSignature)
        assertNull(materialized.rangeMin)
        assertNull(materialized.rangeMax)
        assertEquals(listOf("demo.shared.Public@provider-a#0"), materialized.symbolIdentities)

        val listMaterialized = ProjectedTypeConstructor.materialize(
            ProjectedTypeConstructor.check("consumer", "[uuid]", resolver()),
        )
        assertNull(listMaterialized.baseName)
        assertEquals("uuid", listMaterialized.elementSignature)
        assertTrue(listMaterialized.symbolIdentities.isEmpty())

        val rangeMaterialized = ProjectedTypeConstructor.materialize(
            ProjectedTypeConstructor.check("consumer", "int(-2..4)", resolver()),
        )
        assertEquals("-2", rangeMaterialized.rangeMin)
        assertEquals("4", rangeMaterialized.rangeMax)
    }

    @Test
    fun rejectsGenericsAndNonRangeConstraintsFailClosed() {
        val invalid = listOf(
            "",
            "List<string>",
            "string>",
            "string(min: 1, max: 80)",
            "int(min: 0)",
            "string)",
            "string,uuid",
            "string:uuid",
            "[]",
            "[string",
            "string]",
            "string??",
            "string(1..x)",
            "string(1..2..3)",
            "string(1..2",
            "string()",
            "string(1...2)",
            "123",
        )
        for (source in invalid) {
            assertFailsWith<ProjectedTypeException>(source) { ProjectedTypeConstructor.construct(source) }
        }
    }
}

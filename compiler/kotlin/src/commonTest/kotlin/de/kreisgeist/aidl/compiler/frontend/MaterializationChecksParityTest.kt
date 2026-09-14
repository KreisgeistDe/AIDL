package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class MaterializationChecksParityTest {
    private fun resolver(): ProjectNameResolver = ProjectNameResolver.fromSources(
        listOf(
            "consumer" to """
                module demo.consumer
                import demo.shared.*
                entity Holder {}
            """.trimIndent(),
            "provider-a" to """
                module demo.shared
                export enum PublicEnum {}
                export entity PublicEntity {}
                export entity Duplicate {}
            """.trimIndent(),
            "provider-b" to """
                module demo.shared
                export enum Duplicate {}
            """.trimIndent(),
        ),
    )

    private fun signature(): String {
        val resolver = resolver()
        return listOf(
            "string",
            "PublicEntity",
            "[PublicEntity]?",
            "PublicEntity<PublicEnum>",
            "Page<PublicEntity>",
            "Page<myQuery>",
            "Duplicate",
            "Missing",
        ).joinToString("\n") { type ->
            val check = ProjectedMaterializationChecker.check("consumer", type, resolver)
            "$type|${check.status}|${check.diagnosticCode.orEmpty()}"
        }
    }

    @Test
    fun boundedMaterializationChecksMatchPinnedSignatureDeterministically() {
        val expected = """
            string|MATERIALIZABLE|
            PublicEntity|MATERIALIZABLE|
            [PublicEntity]?|MATERIALIZABLE|
            PublicEntity<PublicEnum>|REJECTED|AIDL-T005
            Page<PublicEntity>|MATERIALIZABLE|
            Page<myQuery>|OUTSIDE_SLICE|
            Duplicate|AMBIGUOUS|CORE-S023
            Missing|UNRESOLVED|AIDL-T001
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun nestedProjectGenericRejectionPropagatesThroughKnownStandardGeneric() {
        val resolver = resolver()
        assertEquals(
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005"),
            ProjectedMaterializationChecker.check(
                "consumer",
                "Page<PublicEntity<PublicEnum>>",
                resolver,
            ),
        )
        assertEquals(
            ProjectedMaterializationStatus.MATERIALIZABLE,
            ProjectedMaterializationChecker.check(
                "consumer",
                "Page<Page<PublicEntity>>",
                resolver,
            ).status,
        )
    }

    @Test
    fun genericProjectResolutionPreservesExistingDiagnostics() {
        val resolver = resolver()
        assertEquals(
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023"),
            ProjectedMaterializationChecker.check("consumer", "Duplicate<PublicEnum>", resolver),
        )
        assertEquals(
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001"),
            ProjectedMaterializationChecker.check("consumer", "Missing<PublicEnum>", resolver),
        )
    }

    @Test
    fun malformedGenericShapesStayOutsideBoundedSlice() {
        val resolver = resolver()
        for (type in listOf(
            "Page<>",
            "Page<PublicEntity,>",
            "Page<PublicEntity",
            "PublicEntity>",
            "<PublicEntity>",
            "Page<PublicEntity,PublicEnum>",
            "Page<Page<PublicEntity>>>",
        )) {
            assertEquals(
                ProjectedMaterializationStatus.OUTSIDE_SLICE,
                ProjectedMaterializationChecker.check("consumer", type, resolver).status,
            )
        }
    }

    @Test
    fun unresolvedAmbiguousAndInvalidNestedStandardArgumentsStayOutsideSlice() {
        val resolver = resolver()
        for (type in listOf("Page<Missing>", "Page<Duplicate>", "Page<bad-name>")) {
            assertEquals(
                ProjectedMaterializationStatus.OUTSIDE_SLICE,
                ProjectedMaterializationChecker.check("consumer", type, resolver).status,
            )
        }
    }

    @Test
    fun unrelatedConstructionFailuresStillFailClosed() {
        assertFailsWith<ProjectedTypeException> {
            ProjectedMaterializationChecker.check("consumer", "", resolver())
        }
    }
}

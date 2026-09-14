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
                query myQuery(id: PublicEntity) -> PublicEntity {}
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
            "myQuery",
            "PublicEntity<PublicEnum>",
            "Page<PublicEntity>",
            "Page<myQuery>",
            "Page<Missing>",
            "Page<Duplicate>",
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
            myQuery|REJECTED|AIDL-T005
            PublicEntity<PublicEnum>|REJECTED|AIDL-T005
            Page<PublicEntity>|MATERIALIZABLE|
            Page<myQuery>|OUTSIDE_SLICE|
            Page<Missing>|UNRESOLVED|AIDL-T001
            Page<Duplicate>|AMBIGUOUS|CORE-S023
            Duplicate|AMBIGUOUS|CORE-S023
            Missing|UNRESOLVED|AIDL-T001
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun resolvedNonMaterializableDeclarationKindIsRejectedWithoutInvalidatingTypeRefIdentity() {
        assertEquals(
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005"),
            ProjectedMaterializationChecker.check("consumer", "myQuery", resolver()),
        )
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
    fun nestedStandardGenericResolutionPreservesFailClosedDiagnostics() {
        val resolver = resolver()
        assertEquals(
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001"),
            ProjectedMaterializationChecker.check("consumer", "Page<Missing>", resolver),
        )
        assertEquals(
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023"),
            ProjectedMaterializationChecker.check("consumer", "Page<Duplicate>", resolver),
        )
    }

    @Test
    fun bindingCoreValidGenericRemainsOutsideHistoricalBoundedSlice() {
        val resolver = resolver()
        val first = ProjectedMaterializationChecker.check("consumer", "Page<myQuery>", resolver)
        val second = ProjectedMaterializationChecker.check("consumer", "Page<myQuery>", resolver)
        assertEquals(ProjectedMaterializationStatus.OUTSIDE_SLICE, first.status)
        assertEquals(null, first.diagnosticCode)
        assertEquals(first, second)
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
    fun invalidNestedStandardArgumentStaysOutsideSlice() {
        assertEquals(
            ProjectedMaterializationStatus.OUTSIDE_SLICE,
            ProjectedMaterializationChecker.check("consumer", "Page<bad-name>", resolver()).status,
        )
    }

    @Test
    fun unrelatedConstructionFailuresStillFailClosed() {
        assertFailsWith<ProjectedTypeException> {
            ProjectedMaterializationChecker.check("consumer", "", resolver())
        }
    }
}

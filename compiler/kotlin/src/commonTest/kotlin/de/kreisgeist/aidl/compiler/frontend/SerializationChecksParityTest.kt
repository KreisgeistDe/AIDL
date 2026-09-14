package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class SerializationChecksParityTest {
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
                export value EmptyValue {}
                export value StructuredValue { field name: string }
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
        val cases = listOf(
            "string",
            "[uuid]?",
            "PublicEnum",
            "PublicEntity",
            "EmptyValue",
            "ref PublicEntity",
            "Duplicate",
            "Missing",
        )
        return cases.joinToString("\n") { type ->
            val check = ProjectedSerializationChecker.check("consumer", type, resolver)
            "$type|${check.status}|${check.diagnosticCode.orEmpty()}"
        }
    }

    @Test
    fun boundedSerializationChecksMatchPinnedSignatureDeterministically() {
        val expected = """
            string|SERIALIZABLE|
            [uuid]?|SERIALIZABLE|
            PublicEnum|SERIALIZABLE|
            PublicEntity|SERIALIZABLE|
            EmptyValue|SERIALIZABLE|
            ref PublicEntity|NOT_SERIALIZABLE|AIDL-T004
            Duplicate|AMBIGUOUS|CORE-S023
            Missing|UNRESOLVED|AIDL-T001
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun complexValueAndBindingCoreGenericRemainOutsideBoundedSlice() {
        val resolver = resolver()
        assertEquals(
            ProjectedSerializationStatus.OUTSIDE_SLICE,
            ProjectedSerializationChecker.check("consumer", "StructuredValue", resolver).status,
        )
        assertEquals(
            ProjectedSerializationStatus.OUTSIDE_SLICE,
            ProjectedSerializationChecker.check("consumer", "Page<myQuery>", resolver).status,
        )
    }

    @Test
    fun refResolutionPreservesFailClosedBoundaries() {
        val resolver = resolver()
        assertEquals(
            ProjectedSerializationCheck(ProjectedSerializationStatus.AMBIGUOUS, "CORE-S023"),
            ProjectedSerializationChecker.check("consumer", "ref Duplicate", resolver),
        )
        assertEquals(
            ProjectedSerializationCheck(ProjectedSerializationStatus.UNRESOLVED, "AIDL-T001"),
            ProjectedSerializationChecker.check("consumer", "ref Missing", resolver),
        )
        assertEquals(
            ProjectedSerializationStatus.OUTSIDE_SLICE,
            ProjectedSerializationChecker.check("consumer", "ref PublicEnum", resolver).status,
        )
        assertEquals(
            ProjectedSerializationStatus.OUTSIDE_SLICE,
            ProjectedSerializationChecker.check("consumer", "ref bad-name", resolver).status,
        )
    }

    @Test
    fun unrelatedConstructionFailuresStillFailClosed() {
        val resolver = resolver()
        assertFailsWith<ProjectedTypeException> {
            ProjectedSerializationChecker.check("consumer", "", resolver)
        }
    }

    @Test
    fun resolvedBuiltinOutsideSelectedPythonScalarSurfaceStaysOutsideSlice() {
        val resolver = resolver()
        assertEquals(
            ProjectedSerializationStatus.OUTSIDE_SLICE,
            ProjectedSerializationChecker.check("consumer", "json", resolver).status,
        )
    }
}

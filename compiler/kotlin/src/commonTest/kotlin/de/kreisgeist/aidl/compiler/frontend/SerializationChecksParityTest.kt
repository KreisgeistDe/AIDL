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
                export value SecretValue { field secret: string sensitive }
                export value StructuredValue { field name: string }
                export entity Duplicate {}
            """.trimIndent(),
            "provider-b" to """
                module demo.shared
                export enum Duplicate {}
            """.trimIndent(),
        ),
    )

    private data class Case(val type: String, val expected: String)

    private fun signature(): String {
        val resolver = resolver()
        val cases = listOf(
            Case("string", "SERIALIZABLE|"),
            Case("[uuid]?", "SERIALIZABLE|"),
            Case("PublicEnum", "SERIALIZABLE|"),
            Case("PublicEntity", "SERIALIZABLE|"),
            Case("EmptyValue", "SERIALIZABLE|"),
            Case("SecretValue", "NOT_SERIALIZABLE|AIDL-T004"),
            Case("Duplicate", "AMBIGUOUS|CORE-S023"),
            Case("Missing", "UNRESOLVED|AIDL-T001"),
        )
        return cases.joinToString("\n") { case ->
            val check = ProjectedSerializationChecker.check("consumer", case.type, resolver)
            "${case.type}|${check.status}|${check.diagnosticCode.orEmpty()}"
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
            SecretValue|NOT_SERIALIZABLE|AIDL-T004
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

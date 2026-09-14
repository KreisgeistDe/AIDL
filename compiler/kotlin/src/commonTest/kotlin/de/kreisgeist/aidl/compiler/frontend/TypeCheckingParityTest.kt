package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class TypeCheckingParityTest {
    private fun resolver(): ProjectNameResolver = ProjectNameResolver.fromSources(
        listOf(
            "resolution-consumer" to """
                module demo.consumer
                import demo.shared.Public
                import demo.shared.*
                entity Local {}
            """.trimIndent(),
            "resolution-provider-a" to """
                module demo.shared
                export value Public {}
                value Hidden {}
                export entity Duplicate {}
            """.trimIndent(),
            "resolution-provider-b" to """
                module demo.shared
                export enum Duplicate {}
                export value Other {}
            """.trimIndent(),
        ),
    )

    private data class Case(val type: String, val literal: String)

    private val cases = listOf(
        Case("string", "\"ok\""),
        Case("bool", "true"),
        Case("int", "-1"),
        Case("decimal", "1"),
        Case("decimal", "1.5"),
        Case("string?", "null"),
        Case("string", "null"),
        Case("int", "true"),
        Case("Duplicate", "\"x\""),
        Case("Missing", "\"x\""),
    )

    private fun signature(): String {
        val resolver = resolver()
        return cases.joinToString("\n") { case ->
            val check = ProjectedTypeChecker.checkDefault(
                "resolution-consumer",
                case.type,
                case.literal,
                resolver,
            )
            "${case.type}|${case.literal}|${check.status}|${check.diagnosticCode.orEmpty()}"
        }
    }

    @Test
    fun boundedTypeCheckingMatchesPinnedParitySignature() {
        val expected = """
            string|"ok"|ASSIGNABLE|
            bool|true|ASSIGNABLE|
            int|-1|ASSIGNABLE|
            decimal|1|ASSIGNABLE|
            decimal|1.5|ASSIGNABLE|
            string?|null|TYPE_MISMATCH|AIDL-T002
            string|null|TYPE_MISMATCH|AIDL-T002
            int|true|TYPE_MISMATCH|AIDL-T002
            Duplicate|"x"|AMBIGUOUS|CORE-S023
            Missing|"x"|UNRESOLVED|AIDL-T001
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun unsupportedShapesAndLiteralsStayOutsideTheBoundedSlice() {
        val resolver = resolver()
        assertEquals(
            ProjectedAssignmentStatus.OUTSIDE_SLICE,
            ProjectedTypeChecker.checkDefault("resolution-consumer", "[uuid]?", "null", resolver).status,
        )
        assertEquals(
            ProjectedAssignmentStatus.OUTSIDE_SLICE,
            ProjectedTypeChecker.checkDefault("resolution-consumer", "Public", "\"x\"", resolver).status,
        )
        assertEquals(
            ProjectedAssignmentStatus.OUTSIDE_SLICE,
            ProjectedTypeChecker.checkDefault("resolution-consumer", "string", "bare", resolver).status,
        )
    }

    @Test
    fun bindingCoreGenericTypeRefDoesNotEscapeHistoricalConstructionException() {
        val resolver = resolver()
        val first = ProjectedTypeChecker.checkDefault(
            "resolution-consumer",
            "Page<myQuery>",
            "\"unused\"",
            resolver,
        )
        val second = ProjectedTypeChecker.checkDefault(
            "resolution-consumer",
            "Page<myQuery>",
            "\"unused\"",
            resolver,
        )

        assertEquals(ProjectedAssignmentStatus.OUTSIDE_SLICE, first.status)
        assertEquals(null, first.diagnosticCode)
        assertEquals(first, second)
    }

    @Test
    fun unrelatedConstructionErrorsStillFailClosed() {
        val resolver = resolver()
        assertFailsWith<ProjectedTypeException> {
            ProjectedTypeChecker.checkDefault("resolution-consumer", "", "\"unused\"", resolver)
        }
    }
}

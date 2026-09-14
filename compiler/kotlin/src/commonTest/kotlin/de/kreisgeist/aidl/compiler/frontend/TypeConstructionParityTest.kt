package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals

class TypeConstructionParityTest {
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

    private data class Case(val label: String, val source: String)

    private val cases = listOf(
        Case("string", "string"),
        Case("[uuid]?", "[uuid]?"),
        Case("Public?", "Public?"),
        Case("demo.shared.Public", "demo.shared.Public"),
        Case("Local", "Local"),
        Case("Duplicate", "Duplicate"),
        Case("Missing", "Missing"),
        Case("<blank>", ""),
        Case("string??", "string??"),
        Case("[string", "[string"),
        Case("string]", "string]"),
    )

    private fun signature(): String {
        val resolver = resolver()
        return cases.joinToString("\n") { case ->
            try {
                val check = ProjectedTypeConstructor.check("resolution-consumer", case.source, resolver)
                val symbols = check.symbols.mapNotNull { it.stableIdentity }.joinToString(",")
                "${case.label}|ACCEPT|${check.status}|$symbols"
            } catch (_: ProjectedTypeException) {
                "${case.label}|REJECT||"
            }
        }
    }

    @Test
    fun boundedTypeConstructionMatchesPinnedParitySignature() {
        val expected = """
            string|ACCEPT|RESOLVED|
            [uuid]?|ACCEPT|RESOLVED|
            Public?|ACCEPT|RESOLVED|demo.shared.Public@resolution-provider-a#0
            demo.shared.Public|ACCEPT|RESOLVED|demo.shared.Public@resolution-provider-a#0
            Local|ACCEPT|RESOLVED|demo.consumer.Local@resolution-consumer#0
            Duplicate|ACCEPT|AMBIGUOUS|demo.shared.Duplicate@resolution-provider-a#2,demo.shared.Duplicate@resolution-provider-b#0
            Missing|ACCEPT|UNRESOLVED|
            <blank>|REJECT||
            string??|REJECT||
            [string|REJECT||
            string]|REJECT||
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }
}

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
        Case("string(1..80)?", "string(1..80)?"),
        Case("Public?", "Public?"),
        Case("demo.shared.Public", "demo.shared.Public"),
        Case("Local", "Local"),
        Case("Duplicate", "Duplicate"),
        Case("Missing", "Missing"),
        Case("<blank>", ""),
        Case("string??", "string??"),
        Case("[string", "[string"),
        Case("string]", "string]"),
        Case("List<string>", "List<string>"),
        Case("string(min:1)", "string(min:1)"),
        Case("string(1..x)", "string(1..x)"),
        Case("string(1..2..3)", "string(1..2..3)"),
    )

    private fun signature(): String {
        val resolver = resolver()
        return cases.joinToString("\n") { case ->
            try {
                val check = ProjectedTypeConstructor.check("resolution-consumer", case.source, resolver)
                val materialized = ProjectedTypeConstructor.materialize(check)
                val symbols = materialized.symbolIdentities.joinToString(",")
                "${case.label}|ACCEPT|${materialized.signature}|${check.status}|$symbols"
            } catch (_: ProjectedTypeException) {
                "${case.label}|REJECT|||"
            }
        }
    }

    @Test
    fun boundedTypeConstructionMatchesPinnedParitySignature() {
        val expected = """
            string|ACCEPT|string|RESOLVED|
            [uuid]?|ACCEPT|[uuid]?|RESOLVED|
            string(1..80)?|ACCEPT|string(1..80)?|RESOLVED|
            Public?|ACCEPT|Public?|RESOLVED|demo.shared.Public@resolution-provider-a#0
            demo.shared.Public|ACCEPT|demo.shared.Public|RESOLVED|demo.shared.Public@resolution-provider-a#0
            Local|ACCEPT|Local|RESOLVED|demo.consumer.Local@resolution-consumer#0
            Duplicate|ACCEPT|Duplicate|AMBIGUOUS|demo.shared.Duplicate@resolution-provider-a#2,demo.shared.Duplicate@resolution-provider-b#0
            Missing|ACCEPT|Missing|UNRESOLVED|
            <blank>|REJECT|||
            string??|REJECT|||
            [string|REJECT|||
            string]|REJECT|||
            List<string>|REJECT|||
            string(min:1)|REJECT|||
            string(1..x)|REJECT|||
            string(1..2..3)|REJECT|||
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }
}

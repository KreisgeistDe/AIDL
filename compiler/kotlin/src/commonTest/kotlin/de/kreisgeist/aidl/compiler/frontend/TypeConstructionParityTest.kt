package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull

class TypeConstructionParityTest {
    private val consumerSource = """
        module demo.consumer
        import demo.shared.Public
        import demo.shared.*
        entity Local {}
    """.trimIndent()

    private fun resolver(): ProjectNameResolver = ProjectNameResolver.fromSources(
        listOf(
            "resolution-consumer" to consumerSource,
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

    private fun diagnosticSignature(): String {
        val anchor = consumerSource.indexOf("entity Local")
        val diagnostics = ProjectedTypeConstructor.diagnosticsAt(
            sourcePath = "resolution-consumer.source",
            sourceText = consumerSource,
            requests = listOf(
                ProjectedTypeDiagnosticRequest(anchor, "entity", "Local", ""),
                ProjectedTypeDiagnosticRequest(anchor, "entity", "Local", "string??"),
                ProjectedTypeDiagnosticRequest(anchor, "entity", "Local", "[string"),
                ProjectedTypeDiagnosticRequest(anchor, "entity", "Local", "string]"),
                ProjectedTypeDiagnosticRequest(anchor, "entity", "Local", "string"),
            ),
        )
        return diagnostics.joinToString("\n") { diagnostic ->
            listOf(
                diagnostic.code,
                diagnostic.phase,
                diagnostic.severity.name.lowercase(),
                diagnostic.message,
                diagnostic.subject.kind,
                diagnostic.subject.name,
                diagnostic.sourcePath,
                diagnostic.location.line.toString(),
                diagnostic.location.column.toString(),
                diagnostic.location.offset.toString(),
                diagnostic.expected,
                diagnostic.docs,
            ).joinToString("|")
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

    @Test
    fun negativeTypeConstructionProjectsStablePythonOwnedDiagnostics() {
        val expected = """
            AIDL-T001|type|error|empty type expression|entity|Local|resolution-consumer.source|4|1|68|well-formed Core type constructor|aidl://diagnostics/AIDL-T001
            AIDL-T001|type|error|invalid Core type expression 'string]'|entity|Local|resolution-consumer.source|4|1|68|well-formed Core type constructor|aidl://diagnostics/AIDL-T001
            AIDL-T001|type|error|list requires one element type|entity|Local|resolution-consumer.source|4|1|68|well-formed Core type constructor|aidl://diagnostics/AIDL-T001
            AIDL-T001|type|error|nullable requires one non-nullable operand|entity|Local|resolution-consumer.source|4|1|68|well-formed Core type constructor|aidl://diagnostics/AIDL-T001
        """.trimIndent()
        assertEquals(expected, diagnosticSignature())
        assertEquals(diagnosticSignature(), diagnosticSignature())
    }

    @Test
    fun typeDiagnosticOrderingUsesOwnedSourceOffsetsBeforeMessages() {
        val anchor = consumerSource.indexOf("entity Local")
        val diagnostics = ProjectedTypeConstructor.diagnosticsAt(
            sourcePath = "resolution-consumer.source",
            sourceText = consumerSource,
            requests = listOf(
                ProjectedTypeDiagnosticRequest(anchor, "entity", "Local", ""),
                ProjectedTypeDiagnosticRequest(0, "module", "demo.consumer", "string??"),
            ),
        )
        assertEquals(listOf(0, anchor), diagnostics.map { it.location.offset })
        assertEquals(listOf(1, 4), diagnostics.map { it.location.line })
    }

    @Test
    fun typeDiagnosticProjectionIsBoundedToRejectedConstructionAndOwnedAnchors() {
        val anchor = consumerSource.indexOf("entity Local")
        assertNull(
            ProjectedTypeConstructor.diagnosticAt(
                sourcePath = "resolution-consumer.source",
                sourceText = consumerSource,
                diagnosticOffset = anchor,
                subjectKind = "entity",
                subjectName = "Local",
                typeSource = "string",
            ),
        )
        for (invalidOffset in listOf(-1, consumerSource.length + 1)) {
            assertFailsWith<IllegalArgumentException> {
                ProjectedTypeConstructor.diagnosticAt(
                    sourcePath = "resolution-consumer.source",
                    sourceText = consumerSource,
                    diagnosticOffset = invalidOffset,
                    subjectKind = "entity",
                    subjectName = "Local",
                    typeSource = "string??",
                )
            }
        }
    }
}

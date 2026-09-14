package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class Gate03DiagnosticLocationParityTest {
    private val source =
        "module demo.consumer\n" +
            "import demo.shared.*\n" +
            "alias RejectedTarget = myQuery\n" +
            "alias MissingTarget = Missing\n" +
            "alias AmbiguousTarget = Duplicate\n" +
            "query WrongDefault(value: string default true) -> string {}\n"

    private fun resolver(): ProjectNameResolver = ProjectNameResolver.fromProjectedDocuments(
        listOf(
            ProjectedDocument(
                "consumer.aidl",
                SourceProjection("demo.consumer", listOf("demo.shared.*"), emptyList()),
            ),
            ProjectedDocument(
                "provider-a.aidl",
                SourceProjection(
                    "demo.shared",
                    emptyList(),
                    listOf(
                        ProjectedDeclaration("query", "myQuery", true, emptyList()),
                        ProjectedDeclaration("entity", "Duplicate", true, emptyList()),
                    ),
                ),
            ),
            ProjectedDocument(
                "provider-b.aidl",
                SourceProjection(
                    "demo.shared",
                    emptyList(),
                    listOf(ProjectedDeclaration("enum", "Duplicate", true, emptyList())),
                ),
            ),
        ),
    )

    private fun offset(marker: String, token: String): Int =
        source.indexOf(marker).also { require(it >= 0) } + marker.length - token.length

    private fun render(label: String, diagnostic: ProjectedGate03Diagnostic): String = buildString {
        append(label).append('|').append(diagnostic.code).append('|')
        append(diagnostic.span.start.line).append(':')
            .append(diagnostic.span.start.column).append(':')
            .append(diagnostic.span.start.offset).append('|')
        append(diagnostic.span.end.line).append(':')
            .append(diagnostic.span.end.column).append(':')
            .append(diagnostic.span.end.offset).append('|')
        append(diagnostic.span.stdoutLocation)
    }

    private fun signature(): String {
        val resolver = resolver()
        val rejected = requireNotNull(
            ProjectedGate03DiagnosticProjector.materialization(
                "consumer.aidl",
                source,
                offset("= myQuery", "myQuery"),
                "myQuery",
                resolver,
            ),
        )
        val missing = requireNotNull(
            ProjectedGate03DiagnosticProjector.resolution(
                "consumer.aidl",
                source,
                offset("= Missing", "Missing"),
                "Missing",
                resolver,
            ),
        )
        val ambiguous = requireNotNull(
            ProjectedGate03DiagnosticProjector.resolution(
                "consumer.aidl",
                source,
                offset("= Duplicate", "Duplicate"),
                "Duplicate",
                resolver,
            ),
        )
        val mismatch = requireNotNull(
            ProjectedGate03DiagnosticProjector.defaultAssignment(
                "consumer.aidl",
                source,
                offset("value: string", "string"),
                "string",
                "true",
                resolver,
            ),
        )
        return listOf(
            render("materialization-rejected", rejected),
            render("resolution-missing", missing),
            render("resolution-ambiguous", ambiguous),
            render("type-mismatch", mismatch),
        ).joinToString("\n")
    }

    @Test
    fun exactGate03DiagnosticLocationsMatchPinnedSignature() {
        val expected = """
            materialization-rejected|AIDL-T005|3:24:65|3:31:72|consumer.aidl:3:24-3:31
            resolution-missing|AIDL-T001|4:23:95|4:30:102|consumer.aidl:4:23-4:30
            resolution-ambiguous|CORE-S023|5:25:127|5:34:136|consumer.aidl:5:25-5:34
            type-mismatch|AIDL-T002|6:27:163|6:33:169|consumer.aidl:6:27-6:33
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun tokenAnchorsFailClosedInsteadOfFallingBackToDeclarationSpans() {
        val resolver = resolver()
        assertFailsWith<IllegalArgumentException> {
            ProjectedGate03DiagnosticProjector.materialization(
                "consumer.aidl",
                source,
                0,
                "myQuery",
                resolver,
            )
        }
        assertFailsWith<IllegalArgumentException> {
            ProjectedGate03DiagnosticProjector.defaultAssignment(
                "consumer.aidl",
                source,
                source.length,
                "string",
                "true",
                resolver,
            )
        }
    }
}

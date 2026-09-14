package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull

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

    private fun render(label: String, diagnostic: ProjectedGate03Diagnostic): String = buildString {
        append(label).append('|').append(diagnostic.code).append('|')
        append(diagnostic.sourcePath.orEmpty()).append('|')
        diagnostic.location?.let {
            append(it.line).append(':').append(it.column).append(':').append(it.offset)
        }
    }

    private fun signature(): String {
        val resolver = resolver()
        val rejected = requireNotNull(
            ProjectedGate03DiagnosticProjector.materialization(
                "consumer.aidl",
                source,
                source.indexOf("alias RejectedTarget"),
                "myQuery",
                resolver,
            ),
        )
        val missing = requireNotNull(
            ProjectedGate03DiagnosticProjector.resolution(
                "consumer.aidl",
                "Missing",
                resolver,
            ),
        )
        val ambiguous = requireNotNull(
            ProjectedGate03DiagnosticProjector.resolution(
                "consumer.aidl",
                "Duplicate",
                resolver,
            ),
        )
        val mismatch = requireNotNull(
            ProjectedGate03DiagnosticProjector.defaultAssignment(
                "consumer.aidl",
                source,
                source.indexOf("query WrongDefault"),
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
    fun exactGate03DiagnosticLocationsMatchPinnedPythonOwnership() {
        val expected = """
            materialization-rejected|AIDL-T005|consumer.aidl|3:1:42
            resolution-missing|AIDL-T001||
            resolution-ambiguous|CORE-S023||
            type-mismatch|AIDL-T002|consumer.aidl|6:1:137
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun declarationAnchorsAreNotReplacedByTypeRefTokenArithmetic() {
        val resolver = resolver()
        val rejected = requireNotNull(
            ProjectedGate03DiagnosticProjector.materialization(
                "consumer.aidl",
                source,
                source.indexOf("alias RejectedTarget"),
                "myQuery",
                resolver,
            ),
        )
        val mismatch = requireNotNull(
            ProjectedGate03DiagnosticProjector.defaultAssignment(
                "consumer.aidl",
                source,
                source.indexOf("query WrongDefault"),
                "string",
                "true",
                resolver,
            ),
        )
        assertEquals(42, rejected.location?.offset)
        assertEquals(137, mismatch.location?.offset)
        assertEquals(65, source.indexOf("myQuery", source.indexOf("alias RejectedTarget")))
        assertEquals(163, source.indexOf("string", source.indexOf("query WrongDefault")))
    }

    @Test
    fun resolverDiagnosticsDoNotFabricateLocations() {
        val resolver = resolver()
        val missing = requireNotNull(
            ProjectedGate03DiagnosticProjector.resolution("consumer.aidl", "Missing", resolver),
        )
        val ambiguous = requireNotNull(
            ProjectedGate03DiagnosticProjector.resolution("consumer.aidl", "Duplicate", resolver),
        )
        assertNull(missing.sourcePath)
        assertNull(missing.location)
        assertNull(ambiguous.sourcePath)
        assertNull(ambiguous.location)
    }

    @Test
    fun nonDiagnosticResultsRemainUnprojected() {
        val resolver = resolver()
        assertNull(
            ProjectedGate03DiagnosticProjector.materialization(
                "consumer.aidl",
                source,
                source.indexOf("query WrongDefault"),
                "string",
                resolver,
            ),
        )
        assertNull(ProjectedGate03DiagnosticProjector.resolution("consumer.aidl", "myQuery", resolver))
        assertNull(
            ProjectedGate03DiagnosticProjector.defaultAssignment(
                "consumer.aidl",
                source,
                source.indexOf("query WrongDefault"),
                "string",
                "\"ok\"",
                resolver,
            ),
        )
    }

    @Test
    fun ownedDiagnosticAnchorsFailClosedOutsideSourceText() {
        val resolver = resolver()
        assertFailsWith<IllegalArgumentException> {
            ProjectedGate03DiagnosticProjector.materialization(
                "consumer.aidl",
                source,
                -1,
                "myQuery",
                resolver,
            )
        }
        assertFailsWith<IllegalArgumentException> {
            ProjectedGate03DiagnosticProjector.defaultAssignment(
                "consumer.aidl",
                source,
                source.length + 1,
                "string",
                "true",
                resolver,
            )
        }
    }
}

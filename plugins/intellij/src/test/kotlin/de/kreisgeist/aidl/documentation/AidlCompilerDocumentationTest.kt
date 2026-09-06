package de.kreisgeist.aidl.documentation

import de.kreisgeist.aidl.diagnostics.AidlProcessOutput
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertContains
import kotlin.test.assertEquals
import kotlin.test.assertIs

class AidlCompilerDocumentationTest {
    private val project = Path.of("/workspace/project")
    private val source = project.resolve("app.aidl")

    @Test
    fun `maps compiler owned declaration and diagnostic documentation`() {
        val runner = AidlProcessRunner { command, _ ->
            assertEquals(
                listOf(
                    "aidl", "document", project.toString(), "--file", source.toString(),
                    "--offset", "42", "--format", "json",
                ),
                command,
            )
            AidlProcessOutput(
                0,
                """{"command":"document","diagnostics":[],"ok":true,"result":{"status":"resolved","declaration":{"fullyQualifiedName":"app.Shared","kind":"entity","location":{"file":"/workspace/project/app.aidl","line":3,"column":8,"offset":20},"representation":"export entity Shared"},"diagnostics":[{"code":"AIDL-R002","phase":"resolve","severity":"error","message":"duplicate declaration","location":{"file":"/workspace/project/app.aidl","line":3,"column":1,"offset":13},"subject":{"kind":"entity","name":"Shared"},"expected":"one declaration","docs":"aidl://diagnostics/AIDL-R002","allowedFixes":[{"kind":"insertClause","text":"example fix"}]}]}}""",
                "",
            )
        }

        val result = assertIs<AidlDocumentationResult.Resolved>(
            AidlCompilerDocumentationAdapter(runner).document(project, source, 42),
        )
        val declaration = requireNotNull(result.declaration)
        assertEquals("app.Shared", declaration.fullyQualifiedName)
        assertEquals("entity", declaration.kind)
        assertEquals("export entity Shared", declaration.representation)
        val diagnostic = result.diagnostics.single()
        assertEquals("AIDL-R002", diagnostic.code)
        assertEquals("resolve", diagnostic.phase)
        assertEquals("error", diagnostic.severity)
        assertEquals("duplicate declaration", diagnostic.message)
        assertEquals("entity", diagnostic.subject?.kind)
        assertEquals("Shared", diagnostic.subject?.name)
        assertEquals("one declaration", diagnostic.expected)
        assertEquals("aidl://diagnostics/AIDL-R002", diagnostic.docs)
        assertEquals("insertClause", diagnostic.allowedFixes.single().kind)
    }

    @Test
    fun `maps unresolved ambiguous and invalid contexts to no documentation`() {
        for (status in listOf("unresolved", "ambiguous", "invalid")) {
            val runner = AidlProcessRunner { _, _ ->
                AidlProcessOutput(
                    0,
                    """{"command":"document","diagnostics":[],"ok":true,"result":{"status":"$status","diagnostics":[]}}""",
                    "",
                )
            }
            assertIs<AidlDocumentationResult.NoDocumentation>(
                AidlCompilerDocumentationAdapter(runner).document(project, source, 1),
            )
        }
    }

    @Test
    fun `does not invent documentation on process compiler or json failures`() {
        assertIs<AidlDocumentationResult.Failure>(
            AidlCompilerDocumentationAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(2, "", "bad") })
                .document(project, source, 1),
        )
        assertIs<AidlDocumentationResult.Failure>(
            AidlCompilerDocumentationAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(70, "{}", "bad") })
                .document(project, source, 1),
        )
        assertIs<AidlDocumentationResult.Failure>(
            AidlCompilerDocumentationAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(0, "not-json", "") })
                .document(project, source, 1),
        )
    }

    @Test
    fun `renderer uses only compiler supplied fields and escapes html`() {
        val result = AidlDocumentationResult.Resolved(
            declaration = AidlDeclarationDocumentation(
                fullyQualifiedName = "app.<Shared>",
                kind = "entity",
                location = AidlDocumentationLocation("/tmp/app.aidl", 2, 8, 12),
                representation = "entity <Shared>",
            ),
            diagnostics = listOf(
                AidlDocumentationDiagnostic(
                    code = "AIDL-X001",
                    phase = "resolve",
                    severity = "warning",
                    message = "compiler <message>",
                    location = AidlDocumentationLocation("/tmp/app.aidl", 2, 1, 5),
                    subject = AidlDocumentationSubject("entity", "Shared"),
                    expected = "compiler expected",
                    docs = "aidl://diagnostics/AIDL-X001",
                    allowedFixes = listOf(AidlDocumentationFix("insertClause", "compiler fix")),
                ),
            ),
        )

        val html = AidlCompilerDocumentationRenderer.render(result)
        assertContains(html, "entity &lt;Shared&gt;")
        assertContains(html, "app.&lt;Shared&gt;")
        assertContains(html, "compiler &lt;message&gt;")
        assertContains(html, "compiler expected")
        assertContains(html, "aidl://diagnostics/AIDL-X001")
        assertContains(html, "insertClause: compiler fix")
    }
}

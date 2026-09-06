package de.kreisgeist.aidl.completion

import de.kreisgeist.aidl.diagnostics.AidlProcessOutput
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs

class AidlCompilerCompletionTest {
    private val project = Path.of("/workspace/project")
    private val source = project.resolve("app.aidl")

    @Test
    fun `maps compiler owned completion candidates`() {
        val runner = AidlProcessRunner { command, _ ->
            assertEquals(
                listOf(
                    "aidl", "complete", project.toString(), "--file", source.toString(),
                    "--offset", "42", "--format", "json",
                ),
                command,
            )
            AidlProcessOutput(
                0,
                """{"command":"complete","diagnostics":[],"ok":true,"result":{"status":"resolved","prefix":"Sha","candidates":[{"insertText":"Shared","displayText":"Shared (entity)","fullyQualifiedName":"lib.Shared","kind":"entity","origin":"exactImport:lib.Shared","location":{"file":"/workspace/project/lib.aidl","offset":10}}]}}""",
                "",
            )
        }

        val result = assertIs<AidlCompletionResult.Resolved>(
            AidlCompilerCompletionAdapter(runner).complete(project, source, 42),
        )
        assertEquals("Sha", result.prefix)
        assertEquals(null, result.qualifier)
        assertEquals(1, result.candidates.size)
        assertEquals("Shared", result.candidates.single().insertText)
        assertEquals("lib.Shared", result.candidates.single().fullyQualifiedName)
        assertEquals("exactImport:lib.Shared", result.candidates.single().origin)
    }

    @Test
    fun `maps compiler rejected declaration context to no candidates`() {
        val runner = AidlProcessRunner { _, _ ->
            AidlProcessOutput(
                0,
                """{"command":"complete","diagnostics":[],"ok":true,"result":{"status":"invalid","candidates":[]}}""",
                "",
            )
        }

        assertIs<AidlCompletionResult.NoCandidates>(
            AidlCompilerCompletionAdapter(runner).complete(project, source, 12),
        )
    }

    @Test
    fun `maps invalid ambiguous and unresolved contexts to no candidates`() {
        for (status in listOf("invalid", "ambiguous", "unresolved")) {
            val runner = AidlProcessRunner { _, _ ->
                AidlProcessOutput(
                    0,
                    """{"command":"complete","diagnostics":[],"ok":true,"result":{"status":"$status","candidates":[]}}""",
                    "",
                )
            }
            assertIs<AidlCompletionResult.NoCandidates>(
                AidlCompilerCompletionAdapter(runner).complete(project, source, 1),
            )
        }
    }

    @Test
    fun `does not invent candidates on process compiler or json failures`() {
        assertIs<AidlCompletionResult.Failure>(
            AidlCompilerCompletionAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(2, "", "bad") })
                .complete(project, source, 1),
        )
        assertIs<AidlCompletionResult.Failure>(
            AidlCompilerCompletionAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(70, "{}", "bad") })
                .complete(project, source, 1),
        )
        assertIs<AidlCompletionResult.Failure>(
            AidlCompilerCompletionAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(0, "not-json", "") })
                .complete(project, source, 1),
        )
    }
}

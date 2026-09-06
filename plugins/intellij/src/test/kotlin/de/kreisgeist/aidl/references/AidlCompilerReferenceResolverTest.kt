package de.kreisgeist.aidl.references

import de.kreisgeist.aidl.diagnostics.AidlProcessOutput
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs

class AidlCompilerReferenceResolverTest {
    private val project = Path.of("/workspace/project")
    private val source = project.resolve("app.aidl")

    @Test
    fun `maps resolved compiler target`() {
        val runner = AidlProcessRunner { command, _ ->
            assertEquals(
                listOf(
                    "aidl", "resolve", project.toString(), "--file", source.toString(),
                    "--offset", "42", "--format", "json",
                ),
                command,
            )
            AidlProcessOutput(
                0,
                """{"command":"resolve","diagnostics":[],"ok":true,"result":{"status":"resolved","reference":"Shared","target":{"fullyQualifiedName":"lib.Shared","kind":"entity","location":{"file":"/workspace/project/lib.aidl","line":2,"column":15,"offset":25}}}}""",
                "",
            )
        }

        val result = AidlCompilerReferenceResolver(runner).resolve(project, source, 42)
        val resolved = assertIs<AidlReferenceResolutionResult.Resolved>(result)
        assertEquals("lib.Shared", resolved.target.fullyQualifiedName)
        assertEquals("entity", resolved.target.kind)
        assertEquals(25, resolved.target.location.offset)
    }

    @Test
    fun `returns no target for unresolved ambiguous and invalid compiler results`() {
        for (status in listOf("unresolved", "ambiguous", "invalid")) {
            val runner = AidlProcessRunner { _, _ ->
                AidlProcessOutput(0, """{"command":"resolve","diagnostics":[],"ok":true,"result":{"status":"$status"}}""", "")
            }
            assertIs<AidlReferenceResolutionResult.NoTarget>(
                AidlCompilerReferenceResolver(runner).resolve(project, source, 1),
            )
        }
    }

    @Test
    fun `does not invent targets on process compiler or json failures`() {
        assertIs<AidlReferenceResolutionResult.Failure>(
            AidlCompilerReferenceResolver(AidlProcessRunner { _, _ -> AidlProcessOutput(2, "", "bad") })
                .resolve(project, source, 1),
        )
        assertIs<AidlReferenceResolutionResult.Failure>(
            AidlCompilerReferenceResolver(AidlProcessRunner { _, _ -> AidlProcessOutput(70, "{}", "bad") })
                .resolve(project, source, 1),
        )
        val malformed = AidlCompilerReferenceResolver(
            AidlProcessRunner { _, _ -> AidlProcessOutput(0, "not-json", "") },
        ).resolve(project, source, 1)
        assertIs<AidlReferenceResolutionResult.Failure>(malformed)
    }
}

package de.kreisgeist.aidl.references

import de.kreisgeist.aidl.diagnostics.AidlProcessOutput
import de.kreisgeist.aidl.diagnostics.AidlProcessRunner
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs

class AidlCompilerRefactoringTest {
    private val project = Path.of("/workspace/project")
    private val source = project.resolve("app.aidl")

    @Test
    fun `maps compiler owned usages`() {
        val runner = AidlProcessRunner { command, _ ->
            assertEquals(
                listOf(
                    "aidl", "usages", project.toString(), "--file", source.toString(),
                    "--offset", "42", "--format", "json",
                ),
                command,
            )
            AidlProcessOutput(
                0,
                """{"command":"usages","diagnostics":[],"ok":true,"result":{"status":"resolved","target":{"fullyQualifiedName":"lib.Shared","kind":"entity","location":{"file":"/workspace/project/lib.aidl","line":2,"column":15,"offset":25}},"usages":[{"file":"/workspace/project/app.aidl","line":4,"column":11,"offset":42,"length":6}]}}""",
                "",
            )
        }

        val result = AidlCompilerRefactoringAdapter(runner).findUsages(project, source, 42)
        val resolved = assertIs<AidlUsagesResult.Resolved>(result)
        assertEquals("lib.Shared", resolved.target.fullyQualifiedName)
        assertEquals(1, resolved.usages.size)
        assertEquals(42, resolved.usages.single().offset)
        assertEquals(6, resolved.usages.single().length)
    }

    @Test
    fun `returns no usages for unresolved ambiguous and invalid compiler results`() {
        for (status in listOf("unresolved", "ambiguous", "invalid")) {
            val runner = AidlProcessRunner { _, _ ->
                AidlProcessOutput(
                    0,
                    """{"command":"usages","diagnostics":[],"ok":true,"result":{"status":"$status","usages":[]}}""",
                    "",
                )
            }
            assertIs<AidlUsagesResult.NoTarget>(
                AidlCompilerRefactoringAdapter(runner).findUsages(project, source, 1),
            )
        }
    }

    @Test
    fun `maps applied and rejected compiler rename outcomes`() {
        val appliedRunner = AidlProcessRunner { command, _ ->
            assertEquals(
                listOf(
                    "aidl", "rename", project.toString(), "--file", source.toString(),
                    "--offset", "10", "--new-name", "Renamed", "--apply", "--format", "json",
                ),
                command,
            )
            AidlProcessOutput(
                0,
                """{"command":"rename","diagnostics":[],"ok":true,"result":{"status":"applied","applied":true,"newFullyQualifiedName":"demo.Renamed","edits":[{"file":"/workspace/project/app.aidl","line":2,"column":8,"offset":10,"length":6,"replacement":"Renamed"}]}}""",
                "",
            )
        }
        val applied = assertIs<AidlRenameResult.Applied>(
            AidlCompilerRefactoringAdapter(appliedRunner).rename(project, source, 10, "Renamed"),
        )
        assertEquals("demo.Renamed", applied.newFullyQualifiedName)
        assertEquals(1, applied.edits.size)

        val rejectedRunner = AidlProcessRunner { _, _ ->
            AidlProcessOutput(
                1,
                """{"command":"rename","diagnostics":[],"ok":false,"result":{"status":"collision","applied":false,"edits":[],"message":"collision"}}""",
                "",
            )
        }
        val rejected = assertIs<AidlRenameResult.Rejected>(
            AidlCompilerRefactoringAdapter(rejectedRunner).rename(project, source, 10, "Renamed"),
        )
        assertEquals("collision", rejected.status)
    }

    @Test
    fun `does not invent refactoring results on infrastructure or json failures`() {
        assertIs<AidlUsagesResult.Failure>(
            AidlCompilerRefactoringAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(2, "", "bad") })
                .findUsages(project, source, 1),
        )
        assertIs<AidlRenameResult.Failure>(
            AidlCompilerRefactoringAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(70, "{}", "bad") })
                .rename(project, source, 1, "Renamed"),
        )
        assertIs<AidlUsagesResult.Failure>(
            AidlCompilerRefactoringAdapter(AidlProcessRunner { _, _ -> AidlProcessOutput(0, "not-json", "") })
                .findUsages(project, source, 1),
        )
    }
}

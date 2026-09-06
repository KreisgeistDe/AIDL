package de.kreisgeist.aidl.diagnostics

import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

class AidlCompilerDiagnosticsAdapterTest {
    private val project = Path.of("fixtures/project")

    @Test
    fun `returns empty diagnostics for successful compiler response`() {
        val adapter = adapterFor(
            AidlProcessOutput(
                exitCode = 0,
                stdout = """{"command":"check","diagnostics":[],"ok":true}""",
                stderr = "",
            ),
        )

        val result = assertIs<AidlDiagnosticResult.Success>(adapter.check(project))

        assertTrue(result.diagnostics.isEmpty())
    }

    @Test
    fun `maps compiler error diagnostics including source location and allowed fixes`() {
        val adapter = adapterFor(
            AidlProcessOutput(
                exitCode = 1,
                stdout = """{"command":"check","diagnostics":[{"code":"AIDL-DIST400","phase":"policy","severity":"error","message":"missing owner","location":{"file":"domain/entity.aidl","line":7,"column":3,"offset":42},"subject":{"kind":"entity","name":"Pet"},"expected":"exactly one owner service","allowedFixes":[{"kind":"add-owner","text":"Add owner service declaration"},{"kind":"remove-extra-owner","text":"Remove duplicate owner declaration"}],"docs":"aidl://diagnostics/AIDL-DIST400"}],"ok":false}""",
                stderr = "",
            ),
        )

        val result = assertIs<AidlDiagnosticResult.Success>(adapter.check(project))
        val diagnostic = result.diagnostics.single()

        assertEquals("AIDL-DIST400", diagnostic.code)
        assertEquals("policy", diagnostic.phase)
        assertEquals(AidlDiagnosticSeverity.ERROR, diagnostic.severity)
        assertEquals("missing owner", diagnostic.message)
        assertEquals(AidlSourceLocation("domain/entity.aidl", 7, 3, 42), diagnostic.location)
        assertEquals(AidlDiagnosticSubject("entity", "Pet"), diagnostic.subject)
        assertEquals("exactly one owner service", diagnostic.expected)
        assertEquals(
            listOf(
                AidlDiagnosticFix("add-owner", "Add owner service declaration"),
                AidlDiagnosticFix("remove-extra-owner", "Remove duplicate owner declaration"),
            ),
            diagnostic.allowedFixes,
        )
        assertEquals("aidl://diagnostics/AIDL-DIST400", diagnostic.docs)
    }

    @Test
    fun `defaults missing allowed fixes to empty list`() {
        val adapter = adapterFor(
            AidlProcessOutput(
                exitCode = 0,
                stdout = """{"command":"check","diagnostics":[{"code":"AIDL-WARN100","phase":"semantic","severity":"warning","message":"warning","location":{"file":"domain/entity.aidl","line":1,"column":1,"offset":0}}],"ok":true}""",
                stderr = "",
            ),
        )

        val result = assertIs<AidlDiagnosticResult.Success>(adapter.check(project))

        assertTrue(result.diagnostics.single().allowedFixes.isEmpty())
    }

    @Test
    fun `reports process execution failures separately`() {
        val adapter = AidlCompilerDiagnosticsAdapter(
            processRunner = AidlProcessRunner { _, _ -> throw IllegalStateException("compiler not found") },
        )

        val result = assertIs<AidlDiagnosticResult.Failure>(adapter.check(project))

        assertEquals(AidlDiagnosticFailureKind.PROCESS, result.kind)
        assertTrue(result.message.contains("compiler not found"))
    }

    @Test
    fun `reports unexpected process exit separately`() {
        val adapter = adapterFor(
            AidlProcessOutput(
                exitCode = 2,
                stdout = "",
                stderr = "usage error",
            ),
        )

        val result = assertIs<AidlDiagnosticResult.Failure>(adapter.check(project))

        assertEquals(AidlDiagnosticFailureKind.PROCESS, result.kind)
        assertEquals(2, result.exitCode)
        assertEquals("usage error", result.stderr)
    }

    @Test
    fun `reports malformed JSON separately`() {
        val adapter = adapterFor(
            AidlProcessOutput(
                exitCode = 0,
                stdout = "not-json",
                stderr = "",
            ),
        )

        val result = assertIs<AidlDiagnosticResult.Failure>(adapter.check(project))

        assertEquals(AidlDiagnosticFailureKind.JSON, result.kind)
        assertEquals(0, result.exitCode)
    }

    @Test
    fun `reports compiler internal failure separately from language diagnostics`() {
        val adapter = adapterFor(
            AidlProcessOutput(
                exitCode = 70,
                stdout = """{"command":"check","diagnostics":[],"error":{"kind":"internal","message":"RuntimeError: boom"},"ok":false}""",
                stderr = "trace omitted",
            ),
        )

        val result = assertIs<AidlDiagnosticResult.Failure>(adapter.check(project))

        assertEquals(AidlDiagnosticFailureKind.COMPILER, result.kind)
        assertEquals(70, result.exitCode)
        assertEquals("RuntimeError: boom", result.message)
        assertEquals("trace omitted", result.stderr)
    }

    @Test
    fun `rejects inconsistent check envelope as JSON response failure`() {
        val adapter = adapterFor(
            AidlProcessOutput(
                exitCode = 1,
                stdout = """{"command":"check","diagnostics":[],"ok":false}""",
                stderr = "",
            ),
        )

        val result = assertIs<AidlDiagnosticResult.Failure>(adapter.check(project))

        assertEquals(AidlDiagnosticFailureKind.JSON, result.kind)
        assertTrue(result.message.contains("exit 1 requires"))
    }

    private fun adapterFor(output: AidlProcessOutput): AidlCompilerDiagnosticsAdapter =
        AidlCompilerDiagnosticsAdapter(
            processRunner = AidlProcessRunner { command, _ ->
                assertEquals("aidl", command.first())
                assertEquals(listOf("check", "--format", "json"), listOf(command[1], command[3], command[4]))
                output
            },
        )
}

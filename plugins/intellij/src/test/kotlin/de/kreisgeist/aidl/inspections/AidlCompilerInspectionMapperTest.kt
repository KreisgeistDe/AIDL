package de.kreisgeist.aidl.inspections

import de.kreisgeist.aidl.diagnostics.AidlCompilerDiagnostic
import de.kreisgeist.aidl.diagnostics.AidlDiagnosticFailureKind
import de.kreisgeist.aidl.diagnostics.AidlDiagnosticFix
import de.kreisgeist.aidl.diagnostics.AidlDiagnosticResult
import de.kreisgeist.aidl.diagnostics.AidlDiagnosticSeverity
import de.kreisgeist.aidl.diagnostics.AidlSourceLocation
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class AidlCompilerInspectionMapperTest {
    private val projectPath = Path.of("/workspace/project")
    private val filePath = projectPath.resolve("domain/entity.aidl")

    @Test
    fun `maps compiler diagnostics for current file preserving code message severity and offset`() {
        val result = AidlDiagnosticResult.Success(
            listOf(
                diagnostic(
                    code = "AIDL-DIST400",
                    severity = AidlDiagnosticSeverity.ERROR,
                    sourcePath = "domain/entity.aidl",
                    offset = 8,
                    line = 1,
                    column = 9,
                ),
                diagnostic(
                    code = "AIDL-WARN100",
                    severity = AidlDiagnosticSeverity.WARNING,
                    sourcePath = "domain/entity.aidl",
                    offset = 13,
                    line = 2,
                    column = 1,
                ),
            ),
        )

        val problems = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = "entity X\nwarning",
        )

        assertEquals(
            listOf(
                AidlInspectionProblem("AIDL-DIST400", "message AIDL-DIST400", AidlDiagnosticSeverity.ERROR, 8),
                AidlInspectionProblem("AIDL-WARN100", "message AIDL-WARN100", AidlDiagnosticSeverity.WARNING, 13),
            ),
            problems,
        )
    }

    @Test
    fun `offers compiler allowed insert clause fixes in source order`() {
        val text = "consumer StartReview {\n  start: workflow Review(event.id)\n}\n"
        val result = AidlDiagnosticResult.Success(
            listOf(
                diagnostic(
                    code = "AIDL-DIST411",
                    severity = AidlDiagnosticSeverity.ERROR,
                    sourcePath = "domain/entity.aidl",
                    offset = 9,
                    line = 1,
                    column = 10,
                    allowedFixes = listOf(
                        AidlDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
                        AidlDiagnosticFix("insertClause", "retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)"),
                    ),
                ),
            ),
        )

        val problem = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = text,
        ).single()

        assertEquals(
            listOf(
                AidlInspectionQuickFix("insertClause", "idempotency: event.eventId retain 30d", filePath),
                AidlInspectionQuickFix(
                    "insertClause",
                    "retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)",
                    filePath,
                ),
            ),
            problem.quickFixes,
        )
    }

    @Test
    fun `inserts compiler clause text after safely mapped opening brace`() {
        val text = "  consumer StartReview {\n    start: workflow Review(event.id)\n  }\n"

        val edit = AidlCompilerQuickFixPlanner.plan(
            kind = "insertClause",
            compilerText = "idempotency: event.eventId retain 30d",
            fileText = text,
            anchorOffset = text.indexOf("StartReview"),
        )

        requireNotNull(edit)
        assertEquals(text.indexOf('\n') + 1, edit.offset)
        assertEquals("    idempotency: event.eventId retain 30d\n", edit.text)
        assertEquals(
            "  consumer StartReview {\n    idempotency: event.eventId retain 30d\n    start: workflow Review(event.id)\n  }\n",
            text.substring(0, edit.offset) + edit.text + text.substring(edit.offset),
        )
    }

    @Test
    fun `does not offer unknown or unsafe compiler fixes`() {
        val result = AidlDiagnosticResult.Success(
            listOf(
                diagnostic(
                    code = "AIDL-DIST411",
                    severity = AidlDiagnosticSeverity.ERROR,
                    sourcePath = "domain/entity.aidl",
                    offset = 9,
                    line = 1,
                    column = 10,
                    allowedFixes = listOf(
                        AidlDiagnosticFix("replaceClause", "idempotency: event.eventId retain 30d"),
                        AidlDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
                    ),
                ),
            ),
        )

        val problem = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = "consumer StartReview\n",
        ).single()

        assertTrue(problem.quickFixes.isEmpty())
    }

    @Test
    fun `maps diagnostics without allowed fixes to no quick fixes`() {
        val result = AidlDiagnosticResult.Success(
            listOf(
                diagnostic(
                    code = "AIDL-DIST400",
                    severity = AidlDiagnosticSeverity.ERROR,
                    sourcePath = "domain/entity.aidl",
                    offset = 9,
                    line = 1,
                    column = 10,
                ),
            ),
        )

        val problem = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = "consumer StartReview {\n}\n",
        ).single()

        assertTrue(problem.quickFixes.isEmpty())
    }

    @Test
    fun `uses line and column when compiler offset is outside current file`() {
        val result = AidlDiagnosticResult.Success(
            listOf(
                diagnostic(
                    code = "AIDL-SEM200",
                    severity = AidlDiagnosticSeverity.INFO,
                    sourcePath = "domain/entity.aidl",
                    offset = 999,
                    line = 2,
                    column = 3,
                ),
            ),
        )

        val problems = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = "first\nsecond",
        )

        assertEquals(8, problems.single().offset)
        assertEquals(AidlDiagnosticSeverity.INFO, problems.single().severity)
    }

    @Test
    fun `ignores diagnostics for other files`() {
        val result = AidlDiagnosticResult.Success(
            listOf(
                diagnostic(
                    code = "AIDL-DIST400",
                    severity = AidlDiagnosticSeverity.ERROR,
                    sourcePath = "domain/other.aidl",
                    offset = 0,
                    line = 1,
                    column = 1,
                    allowedFixes = listOf(
                        AidlDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
                    ),
                ),
            ),
        )

        val problems = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = "consumer StartReview {\n}\n",
        )

        assertTrue(problems.isEmpty())
    }

    @Test
    fun `ignores diagnostics with invalid offset line and column`() {
        val result = AidlDiagnosticResult.Success(
            listOf(
                diagnostic(
                    code = "AIDL-DIST400",
                    severity = AidlDiagnosticSeverity.ERROR,
                    sourcePath = "domain/entity.aidl",
                    offset = 999,
                    line = 99,
                    column = 99,
                    allowedFixes = listOf(
                        AidlDiagnosticFix("insertClause", "idempotency: event.eventId retain 30d"),
                    ),
                ),
            ),
        )

        val problems = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = "consumer StartReview {\n}\n",
        )

        assertTrue(problems.isEmpty())
    }

    @Test
    fun `does not surface infrastructure failures as language problems or fixes`() {
        val result = AidlDiagnosticResult.Failure(
            kind = AidlDiagnosticFailureKind.PROCESS,
            message = "compiler unavailable",
        )

        val problems = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = filePath,
            fileText = "consumer StartReview {\n}\n",
        )

        assertTrue(problems.isEmpty())
    }

    private fun diagnostic(
        code: String,
        severity: AidlDiagnosticSeverity,
        sourcePath: String,
        offset: Int,
        line: Int,
        column: Int,
        allowedFixes: List<AidlDiagnosticFix> = emptyList(),
    ): AidlCompilerDiagnostic = AidlCompilerDiagnostic(
        code = code,
        phase = "semantic",
        severity = severity,
        message = "message $code",
        location = AidlSourceLocation(
            file = sourcePath,
            line = line,
            column = column,
            offset = offset,
        ),
        allowedFixes = allowedFixes,
    )
}

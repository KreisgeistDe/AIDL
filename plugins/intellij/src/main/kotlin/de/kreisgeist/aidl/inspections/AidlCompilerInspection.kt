package de.kreisgeist.aidl.inspections

import com.intellij.codeInspection.LocalInspectionTool
import com.intellij.codeInspection.LocalQuickFix
import com.intellij.codeInspection.ProblemDescriptor
import com.intellij.codeInspection.ProblemHighlightType
import com.intellij.codeInspection.ProblemsHolder
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElementVisitor
import com.intellij.psi.PsiFile
import de.kreisgeist.aidl.AidlFile
import de.kreisgeist.aidl.diagnostics.AidlCompilerDiagnostic
import de.kreisgeist.aidl.diagnostics.AidlCompilerDiagnosticsAdapter
import de.kreisgeist.aidl.diagnostics.AidlDiagnosticFix
import de.kreisgeist.aidl.diagnostics.AidlDiagnosticResult
import de.kreisgeist.aidl.diagnostics.AidlDiagnosticSeverity
import de.kreisgeist.aidl.diagnostics.AidlSourceLocation
import java.nio.file.Path

internal data class AidlInspectionQuickFix(
    val kind: String,
    val text: String,
    val filePath: Path,
)

internal data class AidlInspectionProblem(
    val code: String,
    val message: String,
    val severity: AidlDiagnosticSeverity,
    val offset: Int,
    val quickFixes: List<AidlInspectionQuickFix> = emptyList(),
)

internal data class AidlInsertionEdit(
    val offset: Int,
    val text: String,
)

internal object AidlCompilerQuickFixPlanner {
    private const val INSERT_CLAUSE = "insertClause"

    fun plan(
        kind: String,
        compilerText: String,
        fileText: String,
        anchorOffset: Int,
    ): AidlInsertionEdit? {
        if (kind != INSERT_CLAUSE || compilerText.isEmpty()) return null
        if (anchorOffset !in fileText.indices) return null

        val lineStart = fileText.lastIndexOf('\n', startIndex = anchorOffset).let { if (it < 0) 0 else it + 1 }
        val lineEnd = fileText.indexOf('\n', startIndex = anchorOffset)
        if (lineEnd < 0) return null

        val openBrace = fileText.indexOf('{', startIndex = anchorOffset)
        if (openBrace < 0 || openBrace >= lineEnd) return null

        val indentation = fileText.substring(lineStart, lineEnd).takeWhile { it == ' ' || it == '\t' }
        return AidlInsertionEdit(
            offset = lineEnd + 1,
            text = "$indentation  $compilerText\n",
        )
    }
}

internal class AidlCompilerQuickFix(
    private val fix: AidlInspectionQuickFix,
) : LocalQuickFix {
    override fun getFamilyName(): String = "AIDL compiler quick fixes"

    override fun getName(): String = fix.text

    override fun applyFix(project: Project, descriptor: ProblemDescriptor) {
        val file = descriptor.psiElement.containingFile as? AidlFile ?: return
        val virtualFile = file.virtualFile ?: return
        val currentPath = try {
            Path.of(virtualFile.path).toAbsolutePath().normalize()
        } catch (_: RuntimeException) {
            return
        }
        if (currentPath != fix.filePath) return

        val documentManager = PsiDocumentManager.getInstance(project)
        val document = documentManager.getDocument(file) ?: return
        val edit = AidlCompilerQuickFixPlanner.plan(
            kind = fix.kind,
            compilerText = fix.text,
            fileText = document.text,
            anchorOffset = descriptor.psiElement.textOffset,
        ) ?: return

        document.insertString(edit.offset, edit.text)
        documentManager.commitDocument(document)
    }
}

internal object AidlCompilerInspectionMapper {
    fun problemsForResult(
        result: AidlDiagnosticResult,
        projectPath: Path,
        filePath: Path,
        fileText: String,
    ): List<AidlInspectionProblem> = when (result) {
        is AidlDiagnosticResult.Success -> problemsForDiagnostics(
            diagnostics = result.diagnostics,
            projectPath = projectPath,
            filePath = filePath,
            fileText = fileText,
        )
        is AidlDiagnosticResult.Failure -> emptyList()
    }

    private fun problemsForDiagnostics(
        diagnostics: List<AidlCompilerDiagnostic>,
        projectPath: Path,
        filePath: Path,
        fileText: String,
    ): List<AidlInspectionProblem> {
        val normalizedProject = projectPath.toAbsolutePath().normalize()
        val normalizedFile = filePath.toAbsolutePath().normalize()
        return diagnostics.mapNotNull { diagnostic ->
            val diagnosticFile = resolveDiagnosticPath(normalizedProject, diagnostic.location.file) ?: return@mapNotNull null
            if (diagnosticFile != normalizedFile) return@mapNotNull null
            val offset = resolveOffset(diagnostic.location, fileText) ?: return@mapNotNull null
            AidlInspectionProblem(
                code = diagnostic.code,
                message = diagnostic.message,
                severity = diagnostic.severity,
                offset = offset,
                quickFixes = diagnostic.allowedFixes.mapNotNull { fix ->
                    quickFixFor(
                        fix = fix,
                        filePath = normalizedFile,
                        fileText = fileText,
                        offset = offset,
                    )
                },
            )
        }
    }

    private fun quickFixFor(
        fix: AidlDiagnosticFix,
        filePath: Path,
        fileText: String,
        offset: Int,
    ): AidlInspectionQuickFix? {
        AidlCompilerQuickFixPlanner.plan(
            kind = fix.kind,
            compilerText = fix.text,
            fileText = fileText,
            anchorOffset = offset,
        ) ?: return null
        return AidlInspectionQuickFix(
            kind = fix.kind,
            text = fix.text,
            filePath = filePath,
        )
    }

    private fun resolveDiagnosticPath(projectPath: Path, sourcePath: String): Path? = try {
        val path = Path.of(sourcePath)
        (if (path.isAbsolute) path else projectPath.resolve(path)).toAbsolutePath().normalize()
    } catch (_: RuntimeException) {
        null
    }

    private fun resolveOffset(location: AidlSourceLocation, text: String): Int? {
        if (location.offset in text.indices) return location.offset
        if (location.line < 1 || location.column < 1) return null

        var lineStart = 0
        var line = 1
        while (line < location.line) {
            val newline = text.indexOf('\n', lineStart)
            if (newline < 0) return null
            lineStart = newline + 1
            line += 1
        }

        val lineEnd = text.indexOf('\n', lineStart).let { if (it < 0) text.length else it }
        val candidate = lineStart + location.column - 1
        return candidate.takeIf { it in text.indices && it < lineEnd }
    }
}

class AidlCompilerInspection : LocalInspectionTool() {
    override fun buildVisitor(holder: ProblemsHolder, isOnTheFly: Boolean): PsiElementVisitor {
        if (holder.file !is AidlFile) return PsiElementVisitor.EMPTY_VISITOR
        return object : PsiElementVisitor() {
            private var reported = false

            override fun visitFile(file: PsiFile) {
                if (reported || file !is AidlFile) return
                reported = true
                reportCompilerDiagnostics(file, holder)
            }
        }
    }

    private fun reportCompilerDiagnostics(file: AidlFile, holder: ProblemsHolder) {
        val projectPath = file.project.basePath?.let(Path::of) ?: return
        val sourcePath = file.virtualFile?.path?.let(Path::of) ?: return
        val result = AidlCompilerDiagnosticsAdapter().check(projectPath)
        val problems = AidlCompilerInspectionMapper.problemsForResult(
            result = result,
            projectPath = projectPath,
            filePath = sourcePath,
            fileText = file.text,
        )

        problems.forEach { problem ->
            val element = file.findElementAt(problem.offset) ?: return@forEach
            val quickFixes = problem.quickFixes.map(::AidlCompilerQuickFix).toTypedArray()
            holder.registerProblem(
                element,
                "[${problem.code}] ${problem.message}",
                problemHighlightType(problem.severity),
                *quickFixes,
            )
        }
    }

    private fun problemHighlightType(severity: AidlDiagnosticSeverity): ProblemHighlightType = when (severity) {
        AidlDiagnosticSeverity.ERROR -> ProblemHighlightType.ERROR
        AidlDiagnosticSeverity.WARNING -> ProblemHighlightType.WARNING
        AidlDiagnosticSeverity.INFO -> ProblemHighlightType.INFORMATION
    }
}

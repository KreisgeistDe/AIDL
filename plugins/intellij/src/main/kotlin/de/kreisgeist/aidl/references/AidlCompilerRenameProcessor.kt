package de.kreisgeist.aidl.references

import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiManager
import com.intellij.psi.PsiReference
import com.intellij.psi.search.SearchScope
import com.intellij.psi.util.PsiTreeUtil
import com.intellij.refactoring.listeners.RefactoringElementListener
import com.intellij.refactoring.rename.RenamePsiElementProcessor
import com.intellij.usageView.UsageInfo
import com.intellij.util.IncorrectOperationException
import de.kreisgeist.aidl.psi.AidlNamedElement
import de.kreisgeist.aidl.psi.AidlTypes
import java.nio.file.Path

class AidlCompilerRenameProcessor : RenamePsiElementProcessor() {
    override fun canProcessElement(element: PsiElement): Boolean =
        element is AidlNamedElement && element.node?.elementType == AidlTypes.DECLARATION_NAME

    override fun isToSearchInComments(element: PsiElement): Boolean = false

    override fun isToSearchForTextOccurrences(element: PsiElement): Boolean = false

    override fun findReferences(
        element: PsiElement,
        searchScope: SearchScope,
        searchInCommentsAndStrings: Boolean,
    ): Collection<PsiReference> = AidlCompilerUsageMapper.findReferences(element)

    override fun renameElement(
        element: PsiElement,
        newName: String,
        usages: Array<out UsageInfo>,
        listener: RefactoringElementListener?,
    ) {
        val named = element as? AidlNamedElement
            ?: throw IncorrectOperationException("AIDL compiler rename requires a declaration")
        val projectPath = named.project.basePath?.let(Path::of)
            ?: throw IncorrectOperationException("AIDL project base path is unavailable")
        val sourcePath = named.containingFile.virtualFile?.path?.let(Path::of)
            ?: throw IncorrectOperationException("AIDL source path is unavailable")
        val targetOffset = named.textOffset

        PsiDocumentManager.getInstance(named.project).commitAllDocuments()
        FileDocumentManager.getInstance().saveAllDocuments()

        when (val result = AidlCompilerRefactoringAdapter().rename(projectPath, sourcePath, targetOffset, newName)) {
            is AidlRenameResult.Applied -> {
                val localFileSystem = LocalFileSystem.getInstance()
                result.edits
                    .mapNotNull { edit -> runCatching { Path.of(edit.file).toAbsolutePath().normalize() }.getOrNull() }
                    .distinct()
                    .forEach(localFileSystem::refreshAndFindFileByNioFile)
                val sourceFile = localFileSystem.refreshAndFindFileByNioFile(sourcePath.toAbsolutePath().normalize())
                val psiFile = sourceFile?.let { PsiManager.getInstance(named.project).findFile(it) }
                val renamed = psiFile
                    ?.let { PsiTreeUtil.findChildrenOfType(it, AidlNamedElement::class.java) }
                    ?.firstOrNull { candidate ->
                        candidate.node?.elementType == AidlTypes.DECLARATION_NAME && candidate.name == newName
                    }
                if (renamed != null) {
                    listener?.elementRenamed(renamed)
                }
            }
            is AidlRenameResult.Rejected -> throw IncorrectOperationException(
                result.message ?: "AIDL compiler rejected rename (${result.status})",
            )
            is AidlRenameResult.Failure -> throw IncorrectOperationException(result.message)
        }
    }
}

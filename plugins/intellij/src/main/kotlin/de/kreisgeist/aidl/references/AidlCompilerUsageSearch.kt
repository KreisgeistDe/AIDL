package de.kreisgeist.aidl.references

import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiManager
import com.intellij.psi.PsiReference
import com.intellij.psi.search.searches.ReferencesSearch
import com.intellij.util.Processor
import com.intellij.util.QueryExecutor
import de.kreisgeist.aidl.psi.AidlNamedElement
import de.kreisgeist.aidl.psi.AidlTypes
import java.nio.file.Path

internal object AidlCompilerUsageMapper {
    fun findReferences(element: PsiElement): List<PsiReference> {
        if (element !is AidlNamedElement || element.node?.elementType != AidlTypes.DECLARATION_NAME) {
            return emptyList()
        }
        val projectPath = element.project.basePath?.let(Path::of) ?: return emptyList()
        val sourcePath = element.containingFile.virtualFile?.path?.let(Path::of) ?: return emptyList()
        val result = AidlCompilerRefactoringAdapter().findUsages(
            projectPath = projectPath,
            sourcePath = sourcePath,
            offset = element.textOffset,
        )
        val usages = (result as? AidlUsagesResult.Resolved)?.usages ?: return emptyList()
        return usages.mapNotNull { usage -> referenceAt(element, projectPath, usage) }
    }

    internal fun referenceAt(
        sourceElement: PsiElement,
        projectPath: Path,
        usage: AidlUsageLocation,
    ): PsiReference? {
        val normalizedProject = projectPath.toAbsolutePath().normalize()
        val usagePath = try {
            Path.of(usage.file).toAbsolutePath().normalize()
        } catch (_: RuntimeException) {
            return null
        }
        if (!usagePath.startsWith(normalizedProject) || usage.offset < 0 || usage.length <= 0) return null
        val virtualFile = LocalFileSystem.getInstance().findFileByNioFile(usagePath) ?: return null
        val psiFile = PsiManager.getInstance(sourceElement.project).findFile(virtualFile) ?: return null
        if (usage.offset + usage.length > psiFile.textLength) return null
        val leaf = psiFile.findElementAt(usage.offset) ?: return null
        if (leaf.textOffset != usage.offset || leaf.textLength != usage.length) return null
        return leaf.references.firstOrNull { reference -> reference is AidlReference }
    }
}

class AidlCompilerReferencesSearchExecutor : QueryExecutor<PsiReference, ReferencesSearch.SearchParameters> {
    override fun execute(
        queryParameters: ReferencesSearch.SearchParameters,
        consumer: Processor<in PsiReference>,
    ): Boolean {
        val references = AidlCompilerUsageMapper.findReferences(queryParameters.elementToSearch)
        for (reference in references) {
            if (!consumer.process(reference)) return false
        }
        return true
    }
}

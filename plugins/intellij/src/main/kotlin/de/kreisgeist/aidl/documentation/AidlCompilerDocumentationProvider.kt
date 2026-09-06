package de.kreisgeist.aidl.documentation

import com.intellij.lang.documentation.AbstractDocumentationProvider
import com.intellij.psi.PsiElement
import java.nio.file.Path

class AidlCompilerDocumentationProvider : AbstractDocumentationProvider() {
    override fun generateDoc(element: PsiElement?, originalElement: PsiElement?): String? {
        val position = originalElement ?: element ?: return null
        val file = position.containingFile ?: return null
        val projectPath = file.project.basePath?.let(Path::of) ?: return null
        val sourcePath = file.virtualFile?.path?.let(Path::of) ?: return null
        val result = AidlCompilerDocumentationAdapter().document(
            projectPath = projectPath,
            sourcePath = sourcePath,
            offset = position.textOffset,
        ) as? AidlDocumentationResult.Resolved ?: return null
        return AidlCompilerDocumentationRenderer.render(result)
    }

    override fun getQuickNavigateInfo(element: PsiElement?, originalElement: PsiElement?): String? =
        generateDoc(element, originalElement)
}

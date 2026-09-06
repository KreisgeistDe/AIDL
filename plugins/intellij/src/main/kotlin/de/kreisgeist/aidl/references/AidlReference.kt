package de.kreisgeist.aidl.references

import com.intellij.openapi.util.TextRange
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiElementResolveResult
import com.intellij.psi.PsiPolyVariantReferenceBase
import com.intellij.psi.PsiManager
import com.intellij.psi.ResolveResult
import com.intellij.psi.impl.source.resolve.ResolveCache
import com.intellij.psi.impl.source.resolve.ResolveCache.PolyVariantResolver
import de.kreisgeist.aidl.psi.AidlTypes
import java.nio.file.Path

class AidlReference(element: PsiElement) : PsiPolyVariantReferenceBase<PsiElement>(
    element,
    TextRange(0, element.textLength),
) {
    override fun multiResolve(incompleteCode: Boolean): Array<ResolveResult> =
        ResolveCache.getInstance(element.project).resolveWithCaching(this, RESOLVER, false, incompleteCode)

    override fun resolve(): PsiElement? = multiResolve(false).firstOrNull()?.element

    override fun getVariants(): Array<Any> =
        AidlPsiUtil.importedDeclarations(element.containingFile)
            .map { it.name }
            .distinct()
            .toTypedArray()

    companion object {
        private val RESOLVER = PolyVariantResolver<AidlReference> { reference, _ ->
            val file = reference.element.containingFile
            val projectPath = file.project.basePath?.let(Path::of)
                ?: return@PolyVariantResolver emptyArray()
            val sourcePath = file.virtualFile?.path?.let(Path::of)
                ?: return@PolyVariantResolver emptyArray()
            val resolution = AidlCompilerReferenceResolver().resolve(
                projectPath = projectPath,
                sourcePath = sourcePath,
                offset = reference.element.textOffset,
            )
            val target = (resolution as? AidlReferenceResolutionResult.Resolved)?.target
                ?: return@PolyVariantResolver emptyArray()
            val targetElement = targetElement(reference.element, projectPath, target)
                ?: return@PolyVariantResolver emptyArray()
            arrayOf(PsiElementResolveResult(targetElement))
        }

        internal fun targetElement(
            sourceElement: PsiElement,
            projectPath: Path,
            target: AidlCompilerReferenceTarget,
        ): PsiElement? {
            val normalizedProject = projectPath.toAbsolutePath().normalize()
            val targetPath = try {
                Path.of(target.location.file).toAbsolutePath().normalize()
            } catch (_: RuntimeException) {
                return null
            }
            if (!targetPath.startsWith(normalizedProject)) return null
            if (target.location.offset < 0) return null

            val virtualFile = LocalFileSystem.getInstance().findFileByNioFile(targetPath) ?: return null
            val psiFile = PsiManager.getInstance(sourceElement.project).findFile(virtualFile) ?: return null
            if (target.location.offset >= psiFile.textLength) return null
            var cursor: PsiElement? = psiFile.findElementAt(target.location.offset) ?: return null
            while (cursor != null && cursor.node?.elementType != AidlTypes.DECLARATION_NAME) {
                cursor = cursor.parent
            }
            val declarationName = cursor ?: return null
            val expectedName = target.fullyQualifiedName.substringAfterLast('.')
            return declarationName.takeIf { it.text.replace("\\s+".toRegex(), "").substringAfterLast('.') == expectedName }
        }
    }
}

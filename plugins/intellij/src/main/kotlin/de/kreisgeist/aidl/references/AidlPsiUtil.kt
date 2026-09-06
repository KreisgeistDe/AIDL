package de.kreisgeist.aidl.references

import com.intellij.openapi.project.Project
import com.intellij.openapi.roots.ProjectFileIndex
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiManager
import com.intellij.psi.search.FileTypeIndex
import com.intellij.psi.search.GlobalSearchScope
import com.intellij.psi.tree.IElementType
import com.intellij.psi.util.PsiTreeUtil
import de.kreisgeist.aidl.AidlFile
import de.kreisgeist.aidl.AidlFileType
import de.kreisgeist.aidl.psi.AidlTokenSets
import de.kreisgeist.aidl.psi.AidlTypes

object AidlPsiUtil {
    fun isNameToken(element: PsiElement): Boolean {
        val type = element.node?.elementType
        return type == AidlTypes.IDENTIFIER ||
            type == AidlTypes.TYPE_NAME ||
            type == AidlTypes.PROPERTY_NAME ||
            type in AidlTokenSets.KEYWORDS ||
            type in AidlTokenSets.DECLARATION_KEYWORDS
    }

    fun isDeclarationName(element: PsiElement): Boolean =
        parentElementType(element) == AidlTypes.DECLARATION_NAME

    fun isModuleName(element: PsiElement): Boolean =
        parentElementType(element) == AidlTypes.MODULE_NAME

    fun isImportPath(element: PsiElement): Boolean =
        parentElementType(element) == AidlTypes.IMPORT_PATH

    fun qualifiedNameAt(element: PsiElement): String {
        val parent = element.parent
        val parentType = parent?.node?.elementType
        if (parentType == AidlTypes.DECLARATION_NAME || parentType == AidlTypes.MODULE_NAME || parentType == AidlTypes.IMPORT_PATH) {
            return normalizedQualifiedText(parent.text)
        }

        val parts = mutableListOf<String>()
        var left: PsiElement? = element
        while (left != null && isNameOrDot(left)) {
            left = left.prevSibling
        }

        var cursor: PsiElement? = left?.nextSibling ?: element
        while (cursor != null && isNameOrDot(cursor)) {
            val type = cursor.node?.elementType
            if (isNameToken(cursor)) {
                parts += cursor.text
            } else if (type == AidlTypes.DOT) {
                parts += "."
            }
            cursor = cursor.nextSibling
        }

        return normalizedQualifiedText(parts.joinToString(""))
    }

    fun moduleName(file: PsiFile): String? =
        file.node.findChildByType(AidlTypes.MODULE_DECLARATION)
            ?.findChildByType(AidlTypes.MODULE_NAME)
            ?.text
            ?.let(::normalizedQualifiedText)
            ?.takeIf { it.isNotBlank() }

    fun imports(file: PsiFile): List<AidlImport> =
        file.node.getChildren(null)
            .asSequence()
            .filter { it.elementType == AidlTypes.IMPORT_DECLARATION }
            .mapNotNull { node ->
                val text = node.findChildByType(AidlTypes.IMPORT_PATH)?.text ?: return@mapNotNull null
                val normalized = normalizedQualifiedText(text)
                if (normalized.isBlank()) {
                    null
                } else {
                    AidlImport(normalized.removeSuffix(".*"), normalized.endsWith(".*"))
                }
            }
            .toList()

    fun declarations(file: PsiFile): List<AidlDefinition> {
        val moduleName = moduleName(file)
        return PsiTreeUtil.collectElements(file) { it.node?.elementType == AidlTypes.DECLARATION_NAME }
            .mapNotNull { nameElement ->
                val name = normalizedQualifiedText(nameElement.text).substringAfterLast('.')
                if (name.isBlank()) {
                    null
                } else {
                    val qualifiedName = if (moduleName == null) name else "$moduleName.$name"
                    AidlDefinition(name, qualifiedName, nameElement)
                }
            }
    }

    fun projectDeclarations(project: Project): List<AidlDefinition> =
        aidlFiles(project).flatMap { file ->
            val psiFile = PsiManager.getInstance(project).findFile(file) as? AidlFile
            if (psiFile == null) emptyList() else declarations(psiFile)
        }

    fun projectModules(project: Project): List<AidlDefinition> =
        aidlFiles(project).mapNotNull { file ->
            val psiFile = PsiManager.getInstance(project).findFile(file) as? AidlFile ?: return@mapNotNull null
            val moduleElement = psiFile.node.findChildByType(AidlTypes.MODULE_DECLARATION)
                ?.findChildByType(AidlTypes.MODULE_NAME)
                ?.psi ?: return@mapNotNull null
            val moduleName = normalizedQualifiedText(moduleElement.text).takeIf { it.isNotBlank() } ?: return@mapNotNull null
            AidlDefinition(moduleName.substringAfterLast('.'), moduleName, moduleElement)
        }

    fun projectModuleFiles(project: Project): List<AidlModuleFile> =
        aidlFiles(project).mapNotNull { file ->
            val psiFile = PsiManager.getInstance(project).findFile(file) as? AidlFile ?: return@mapNotNull null
            val moduleName = moduleName(psiFile) ?: return@mapNotNull null
            val sourceRoot = inferSourceRoot(project, file, moduleName)
            AidlModuleFile(moduleName, file.nameWithoutExtension, file, sourceRoot)
        }

    fun importPathPrefixAt(element: PsiElement): String? =
        pathPrefixAt(element, AidlTypes.IMPORT_PATH)

    fun moduleNamePrefixAt(element: PsiElement): String? =
        pathPrefixAt(element, AidlTypes.MODULE_NAME)

    fun importedDeclarations(file: PsiFile): List<AidlDefinition> {
        val project = file.project
        val currentModule = moduleName(file)
        val imports = imports(file)
        val all = projectDeclarations(project)

        return all.filter { definition ->
            val qualifiedName = definition.qualifiedName ?: return@filter false
            val declarationModule = qualifiedName.substringBeforeLast('.', "")
            declarationModule == currentModule ||
                imports.any { import ->
                    if (import.wildcard) {
                        declarationModule == import.path
                    } else {
                        qualifiedName == import.path
                    }
                }
        }.ifEmpty {
            all
        }
    }

    private fun aidlFiles(project: Project): Collection<VirtualFile> =
        FileTypeIndex.getFiles(AidlFileType.INSTANCE, GlobalSearchScope.projectScope(project))

    private fun pathPrefixAt(element: PsiElement, parentType: IElementType): String? {
        val parent = element.parent?.takeIf { it.node?.elementType == parentType } ?: return null
        val parts = mutableListOf<String>()
        var cursor = parent.firstChild
        while (cursor != null) {
            when {
                isNameToken(cursor) -> {
                    parts += cursor.text
                    if (cursor == element) {
                        return normalizedQualifiedText(parts.joinToString(""))
                    }
                }
                cursor.node?.elementType == AidlTypes.DOT -> parts += "."
            }
            cursor = cursor.nextSibling
        }
        return null
    }

    private fun inferSourceRoot(project: Project, file: VirtualFile, moduleName: String): VirtualFile? {
        val moduleTail = moduleName.split(".").drop(1)
        var cursor: VirtualFile? = file.parent
        for (segment in moduleTail.dropLast(1).asReversed()) {
            if (cursor?.name != segment) {
                return ProjectFileIndex.getInstance(project).getContentRootForFile(file) ?: file.parent
            }
            cursor = cursor.parent
        }
        return cursor ?: ProjectFileIndex.getInstance(project).getContentRootForFile(file)
    }

    private fun parentElementType(element: PsiElement): IElementType? =
        element.parent?.node?.elementType

    private fun isNameOrDot(element: PsiElement): Boolean =
        isNameToken(element) || element.node?.elementType == AidlTypes.DOT

    private fun normalizedQualifiedText(text: String): String =
        text.replace("\\s+".toRegex(), "").trim()
}

data class AidlImport(
    val path: String,
    val wildcard: Boolean,
)

data class AidlModuleFile(
    val moduleName: String,
    val fileStem: String,
    val file: VirtualFile,
    val sourceRoot: VirtualFile?,
) {
    val fileQualifiedName: String = "$moduleName.$fileStem"
}

package de.kreisgeist.aidl.psi

import com.intellij.lang.ASTNode
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiNameIdentifierOwner

class AidlNamedElement(node: ASTNode) : AidlElement(node), PsiNameIdentifierOwner {
    override fun getName(): String = text.replace("\\s+".toRegex(), "").substringAfterLast('.')

    override fun getNameIdentifier(): PsiElement? =
        children.lastOrNull { child ->
            val type = child.node?.elementType
            type == AidlTypes.IDENTIFIER ||
                type == AidlTypes.TYPE_NAME ||
                type == AidlTypes.PROPERTY_NAME ||
                type in AidlTokenSets.KEYWORDS ||
                type in AidlTokenSets.DECLARATION_KEYWORDS
        }

    override fun setName(name: String): PsiElement {
        val identifier = nameIdentifier ?: return this
        val document = containingFile.viewProvider.document ?: return this
        val range = identifier.textRange
        document.replaceString(range.startOffset, range.endOffset, name)
        return this
    }

    override fun getTextOffset(): Int = nameIdentifier?.textOffset ?: super.getTextOffset()

    fun nameRangeInElement(): TextRange {
        val identifier = nameIdentifier ?: return TextRange.EMPTY_RANGE
        return TextRange.from(identifier.startOffsetInParent, identifier.textLength)
    }
}

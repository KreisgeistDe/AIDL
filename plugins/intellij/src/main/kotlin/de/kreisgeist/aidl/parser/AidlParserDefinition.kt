package de.kreisgeist.aidl.parser

import com.intellij.lang.ASTNode
import com.intellij.lang.ParserDefinition
import com.intellij.lang.PsiParser
import com.intellij.lexer.Lexer
import com.intellij.openapi.project.Project
import com.intellij.psi.FileViewProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.TokenType
import com.intellij.psi.tree.IFileElementType
import com.intellij.psi.tree.TokenSet
import de.kreisgeist.aidl.AidlFile
import de.kreisgeist.aidl.AidlLanguage
import de.kreisgeist.aidl.lexer.AidlLexer
import de.kreisgeist.aidl.psi.AidlElement
import de.kreisgeist.aidl.psi.AidlNamedElement
import de.kreisgeist.aidl.psi.AidlTokenSets
import de.kreisgeist.aidl.psi.AidlTypes

class AidlParserDefinition : ParserDefinition {
    override fun createLexer(project: Project?): Lexer = AidlLexer()

    override fun createParser(project: Project?): PsiParser = AidlParser()

    override fun getFileNodeType(): IFileElementType = FILE

    override fun getWhitespaceTokens(): TokenSet = WHITE_SPACES

    override fun getCommentTokens(): TokenSet = AidlTokenSets.COMMENTS

    override fun getStringLiteralElements(): TokenSet = AidlTokenSets.STRINGS

    override fun createElement(node: ASTNode): PsiElement = when (node.elementType) {
        AidlTypes.DECLARATION_NAME, AidlTypes.MODULE_NAME -> AidlNamedElement(node)
        else -> AidlElement(node)
    }

    override fun createFile(viewProvider: FileViewProvider): PsiFile = AidlFile(viewProvider)

    override fun spaceExistenceTypeBetweenTokens(left: ASTNode?, right: ASTNode?): ParserDefinition.SpaceRequirements =
        ParserDefinition.SpaceRequirements.MAY

    companion object {
        val FILE = IFileElementType(AidlLanguage)
        val WHITE_SPACES: TokenSet = TokenSet.create(TokenType.WHITE_SPACE)
        val COMMENT_TOKENS: TokenSet = AidlTokenSets.COMMENTS
        val STRING_LITERALS: TokenSet = AidlTokenSets.STRINGS
    }
}

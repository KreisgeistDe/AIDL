package de.kreisgeist.aidl.highlighting

import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.HighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.psi.TokenType
import com.intellij.psi.tree.IElementType
import de.kreisgeist.aidl.lexer.AidlLexer
import de.kreisgeist.aidl.psi.AidlTokenSets
import de.kreisgeist.aidl.psi.AidlTypes

class AidlSyntaxHighlighter : SyntaxHighlighterBase() {
    override fun getHighlightingLexer(): Lexer = AidlLexer()

    override fun getTokenHighlights(tokenType: IElementType): Array<TextAttributesKey> = when {
        tokenType == TokenType.BAD_CHARACTER -> pack(BAD_CHARACTER)
        tokenType in AidlTokenSets.DECLARATION_KEYWORDS -> pack(DECLARATION_KEYWORD)
        tokenType in AidlTokenSets.SCALAR_TYPES -> pack(SCALAR_TYPE)
        tokenType == AidlTypes.PROPERTY_NAME -> pack(PROPERTY_NAME)
        tokenType in AidlTokenSets.KEYWORDS -> pack(KEYWORD)
        tokenType in AidlTokenSets.COMMENTS -> pack(COMMENT)
        tokenType in AidlTokenSets.STRINGS -> pack(STRING)
        tokenType in AidlTokenSets.NUMBERS -> pack(NUMBER)
        tokenType in AidlTokenSets.OPERATORS -> pack(OPERATOR)
        tokenType in AidlTokenSets.BRACES -> pack(BRACES)
        tokenType == AidlTypes.ANNOTATION_NAME || tokenType == AidlTypes.AT -> pack(ANNOTATION)
        tokenType == AidlTypes.TYPE_NAME -> pack(TYPE_NAME)
        tokenType == AidlTypes.IDENTIFIER -> pack(IDENTIFIER)
        else -> TextAttributesKey.EMPTY_ARRAY
    }

    companion object {
        val KEYWORD: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_KEYWORD",
            DefaultLanguageHighlighterColors.KEYWORD,
        )
        val DECLARATION_KEYWORD: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_DECLARATION_KEYWORD",
            DefaultLanguageHighlighterColors.KEYWORD,
        )
        val SCALAR_TYPE: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_SCALAR_TYPE",
            DefaultLanguageHighlighterColors.KEYWORD,
        )
        val PROPERTY_NAME: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_PROPERTY_NAME",
            DefaultLanguageHighlighterColors.KEYWORD,
        )
        val IDENTIFIER: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_IDENTIFIER",
            DefaultLanguageHighlighterColors.IDENTIFIER,
        )
        val TYPE_NAME: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_TYPE_NAME",
            DefaultLanguageHighlighterColors.CLASS_NAME,
        )
        val STRING: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_STRING",
            DefaultLanguageHighlighterColors.STRING,
        )
        val NUMBER: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_NUMBER",
            DefaultLanguageHighlighterColors.NUMBER,
        )
        val COMMENT: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_COMMENT",
            DefaultLanguageHighlighterColors.LINE_COMMENT,
        )
        val ANNOTATION: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_ANNOTATION",
            DefaultLanguageHighlighterColors.METADATA,
        )
        val OPERATOR: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_OPERATOR",
            DefaultLanguageHighlighterColors.OPERATION_SIGN,
        )
        val BRACES: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_BRACES",
            DefaultLanguageHighlighterColors.BRACES,
        )
        val BAD_CHARACTER: TextAttributesKey = TextAttributesKey.createTextAttributesKey(
            "AIDL_BAD_CHARACTER",
            HighlighterColors.BAD_CHARACTER,
        )
    }
}

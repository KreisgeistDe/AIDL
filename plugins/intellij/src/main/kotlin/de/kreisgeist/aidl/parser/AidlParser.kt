package de.kreisgeist.aidl.parser

import com.intellij.lang.ASTNode
import com.intellij.lang.PsiBuilder
import com.intellij.lang.PsiParser
import com.intellij.psi.tree.IElementType
import de.kreisgeist.aidl.psi.AidlTokenSets
import de.kreisgeist.aidl.psi.AidlTypes

class AidlParser : PsiParser {
    override fun parse(root: IElementType, builder: PsiBuilder): ASTNode {
        val rootMarker = builder.mark()
        while (!builder.eof()) {
            parseTopLevelItem(builder)
        }
        rootMarker.done(root)
        return builder.treeBuilt
    }

    private fun parseTopLevelItem(builder: PsiBuilder) {
        val item = builder.mark()
        when (builder.tokenType) {
            AidlTypes.MODULE_KEYWORD -> {
                builder.advanceLexer()
                parseQualifiedName(builder, AidlTypes.MODULE_NAME)
                parseUntilLineEnd(builder)
                item.done(AidlTypes.MODULE_DECLARATION)
            }
            AidlTypes.IMPORT_KEYWORD -> {
                builder.advanceLexer()
                parseQualifiedName(builder, AidlTypes.IMPORT_PATH, allowWildcard = true)
                parseUntilLineEnd(builder)
                item.done(AidlTypes.IMPORT_DECLARATION)
            }
            AidlTypes.EXPORT_KEYWORD -> {
                builder.advanceLexer()
                parseAnnotatedDeclarationBody(builder)
                item.done(AidlTypes.EXPORT_DECLARATION)
            }
            AidlTypes.ANNOTATION_NAME -> {
                while (builder.tokenType == AidlTypes.ANNOTATION_NAME) {
                    parseAnnotation(builder)
                }
                parseAnnotatedDeclarationBody(builder)
                item.done(AidlTypes.DECLARATION)
            }
            else -> {
                parseAnnotatedDeclarationBody(builder)
                item.done(AidlTypes.DECLARATION)
            }
        }
    }

    private fun parseAnnotatedDeclarationBody(builder: PsiBuilder) {
        if (builder.tokenType in AidlTokenSets.DECLARATION_KEYWORDS) {
            parseDeclaration(builder)
        } else {
            builder.advanceLexer()
        }
    }

    private fun parseDeclaration(builder: PsiBuilder) {
        val declarationKeyword = builder.tokenType
        builder.advanceLexer()
        parseDeclarationName(builder, declarationKeyword)
        var braceDepth = 0
        while (!builder.eof()) {
            when (builder.tokenType) {
                AidlTypes.LBRACE -> {
                    braceDepth++
                    builder.advanceLexer()
                }
                AidlTypes.RBRACE -> {
                    builder.advanceLexer()
                    braceDepth--
                    if (braceDepth <= 0) {
                        return
                    }
                }
                AidlTypes.NEWLINE -> {
                    builder.advanceLexer()
                    if (braceDepth == 0) {
                        return
                    }
                }
                else -> builder.advanceLexer()
            }
        }
    }

    private fun parseDeclarationName(builder: PsiBuilder, declarationKeyword: IElementType?) {
        if (declarationKeyword == AidlTypes.NATIVE_KEYWORD) {
            skipTrivia(builder)
            builder.advanceLexer()
        } else if (declarationKeyword == AidlTypes.TENANT_KEYWORD) {
            skipTrivia(builder)
            builder.advanceLexer()
        }

        skipTrivia(builder)
        if (builder.tokenType == AidlTypes.STRING) {
            return
        }
        parseQualifiedName(builder, AidlTypes.DECLARATION_NAME)
    }

    private fun parseAnnotation(builder: PsiBuilder) {
        val marker = builder.mark()
        builder.advanceLexer()
        if (builder.tokenType == AidlTypes.LPAREN) {
            var parenDepth = 0
            do {
                when (builder.tokenType) {
                    AidlTypes.LPAREN -> parenDepth++
                    AidlTypes.RPAREN -> parenDepth--
                }
                builder.advanceLexer()
            } while (!builder.eof() && parenDepth > 0)
        }
        marker.done(AidlTypes.ANNOTATION)
    }

    private fun parseUntilLineEnd(builder: PsiBuilder) {
        while (!builder.eof()) {
            val tokenType = builder.tokenType
            builder.advanceLexer()
            if (tokenType == AidlTypes.NEWLINE) {
                break
            }
        }
    }

    private fun parseQualifiedName(builder: PsiBuilder, elementType: IElementType, allowWildcard: Boolean = false) {
        if (!isNameToken(builder.tokenType)) {
            return
        }
        val marker = builder.mark()
        builder.advanceLexer()
        while (builder.tokenType == AidlTypes.DOT) {
            builder.advanceLexer()
            if (allowWildcard && builder.tokenType == AidlTypes.STAR) {
                builder.advanceLexer()
                break
            }
            if (!isNameToken(builder.tokenType)) {
                break
            }
            builder.advanceLexer()
        }
        marker.done(elementType)
    }

    private fun skipTrivia(builder: PsiBuilder) {
        while (
            builder.tokenType == AidlTypes.NEWLINE ||
            builder.tokenType == AidlTypes.LINE_COMMENT ||
            builder.tokenType == AidlTypes.BLOCK_COMMENT_START ||
            builder.tokenType == AidlTypes.BLOCK_COMMENT_CONTENT ||
            builder.tokenType == AidlTypes.BLOCK_COMMENT_END
        ) {
            builder.advanceLexer()
        }
    }

    private fun isNameToken(type: IElementType?): Boolean =
        type == AidlTypes.IDENTIFIER ||
            type == AidlTypes.TYPE_NAME ||
            type == AidlTypes.PROPERTY_NAME ||
            type in AidlTokenSets.KEYWORDS ||
            type in AidlTokenSets.DECLARATION_KEYWORDS
}

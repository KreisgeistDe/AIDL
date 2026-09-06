package de.kreisgeist.aidl.lexer

import com.intellij.lexer.LexerBase
import com.intellij.psi.TokenType
import com.intellij.psi.tree.IElementType
import de.kreisgeist.aidl.psi.AidlTypes

class AidlLexer : LexerBase() {
    private var buffer: CharSequence = ""
    private var startOffset = 0
    private var endOffset = 0
    private var inBlockComment = false
    private var braceDepth = 0
    private var tokenStart = 0
    private var tokenEnd = 0
    private var tokenType: IElementType? = null

    override fun start(buffer: CharSequence, startOffset: Int, endOffset: Int, initialState: Int) {
        this.buffer = buffer
        this.startOffset = startOffset
        this.endOffset = endOffset
        this.inBlockComment = initialState and BLOCK_COMMENT_FLAG != 0
        this.braceDepth = initialState ushr BRACE_DEPTH_SHIFT
        this.tokenStart = startOffset
        this.tokenEnd = startOffset
        locateToken()
    }

    override fun getState() = (braceDepth shl BRACE_DEPTH_SHIFT) or if (inBlockComment) BLOCK_COMMENT_FLAG else 0

    override fun getTokenType(): IElementType? = tokenType

    override fun getTokenStart() = tokenStart

    override fun getTokenEnd() = tokenEnd

    override fun advance() {
        tokenStart = tokenEnd
        locateToken()
    }

    override fun getBufferSequence(): CharSequence = buffer

    override fun getBufferEnd() = endOffset

    private fun locateToken() {
        if (tokenStart >= endOffset) {
            tokenType = null
            tokenEnd = tokenStart
            return
        }

        if (inBlockComment) {
            scanBlockCommentContent()
            return
        }

        val c = buffer[tokenStart]
        when {
            c == ' ' || c == '\t' || c == '\u000c' -> scanWhile(TokenType.WHITE_SPACE) {
                it == ' ' || it == '\t' || it == '\u000c'
            }
            c == '\r' || c == '\n' -> scanNewline()
            startsWith("//") -> scanLineComment()
            startsWith("/*") -> {
                tokenEnd = tokenStart + 2
                tokenType = AidlTypes.BLOCK_COMMENT_START
                inBlockComment = true
            }
            c == '"' -> scanString(AidlTypes.STRING, '"')
            c == '/' && isRegexStart() -> scanString(AidlTypes.REGEX, '/')
            c == '@' && tokenStart + 1 < endOffset && isIdentifierStart(buffer[tokenStart + 1]) -> scanAnnotationName()
            c == '-' && tokenStart + 1 < endOffset && buffer[tokenStart + 1].isDigit() -> scanNumber()
            c.isDigit() -> scanNumber()
            isIdentifierStart(c) -> scanIdentifier()
            else -> scanOperatorOrBadChar()
        }
    }

    private fun scanBlockCommentContent() {
        if (startsWith("*/")) {
            tokenEnd = tokenStart + 2
            tokenType = AidlTypes.BLOCK_COMMENT_END
            inBlockComment = false
            return
        }

        var index = tokenStart
        while (index < endOffset && !startsWith("*/", index)) {
            index++
        }
        tokenEnd = index
        tokenType = AidlTypes.BLOCK_COMMENT_CONTENT
    }

    private fun scanLineComment() {
        var index = tokenStart + 2
        while (index < endOffset && buffer[index] != '\r' && buffer[index] != '\n') {
            index++
        }
        tokenEnd = index
        tokenType = AidlTypes.LINE_COMMENT
    }

    private fun scanNewline() {
        tokenEnd = if (buffer[tokenStart] == '\r' && tokenStart + 1 < endOffset && buffer[tokenStart + 1] == '\n') {
            tokenStart + 2
        } else {
            tokenStart + 1
        }
        tokenType = AidlTypes.NEWLINE
    }

    private fun scanString(type: IElementType, delimiter: Char) {
        var index = tokenStart + 1
        var escaped = false
        while (index < endOffset) {
            val c = buffer[index]
            if (escaped) {
                escaped = false
            } else if (c == '\\') {
                escaped = true
            } else if (c == delimiter) {
                index++
                break
            } else if (c == '\r' || c == '\n') {
                break
            }
            index++
        }
        tokenEnd = index
        tokenType = type
    }

    private fun scanAnnotationName() {
        var index = tokenStart + 2
        while (index < endOffset && isIdentifierPart(buffer[index])) {
            index++
        }
        tokenEnd = index
        tokenType = AidlTypes.ANNOTATION_NAME
    }

    private fun scanNumber() {
        var index = tokenStart
        if (buffer[index] == '-') {
            index++
        }
        while (index < endOffset && buffer[index].isDigit()) {
            index++
        }

        var hasDecimal = false
        if (index + 1 < endOffset && buffer[index] == '.' && buffer[index + 1].isDigit()) {
            hasDecimal = true
            index++
            while (index < endOffset && buffer[index].isDigit()) {
                index++
            }
        }

        val suffixStart = index
        while (index < endOffset && buffer[index].isLetter()) {
            index++
        }
        if (index < endOffset && buffer[index] == '%') {
            index++
            tokenEnd = index
            tokenType = AidlTypes.PERCENTAGE
            return
        }

        val suffix = buffer.subSequence(suffixStart, index).toString()
        tokenEnd = index
        tokenType = when (suffix) {
            "ms", "s", "m", "h", "d" -> AidlTypes.DURATION_LITERAL
            "B", "KB", "MB", "GB", "TB" -> AidlTypes.BYTE_LITERAL
            "mCPU", "core", "cores" -> AidlTypes.CPU_LITERAL
            "" -> if (hasDecimal) AidlTypes.DECIMAL_LITERAL else AidlTypes.INTEGER
            else -> AidlTypes.INTEGER
        }
        if (suffix.isNotEmpty() && tokenType == AidlTypes.INTEGER) {
            tokenEnd = suffixStart
        }
    }

    private fun scanIdentifier() {
        var index = tokenStart + 1
        while (index < endOffset && isIdentifierPart(buffer[index])) {
            index++
        }
        val text = buffer.subSequence(tokenStart, index).toString()
        tokenEnd = index
        tokenType = (if (previousSignificantChar() == '.') {
            null
        } else if (braceDepth > 0 && AidlTypes.isPropertyName(text)) {
            AidlTypes.PROPERTY_NAME
        } else {
            AidlTypes.keyword(text, isDeclarationKeywordPosition())
        })
            ?: if (buffer[tokenStart].isUpperCase()) AidlTypes.TYPE_NAME else AidlTypes.IDENTIFIER
    }

    private fun scanOperatorOrBadChar() {
        val two = if (tokenStart + 1 < endOffset) {
            buffer.subSequence(tokenStart, tokenStart + 2).toString()
        } else {
            ""
        }
        val three = if (tokenStart + 2 < endOffset) {
            buffer.subSequence(tokenStart, tokenStart + 3).toString()
        } else {
            ""
        }

        val type = when {
            three == "..." -> AidlTypes.SPREAD
            two == "->" -> AidlTypes.ARROW
            two == ".." -> AidlTypes.RANGE
            two == "==" -> AidlTypes.EQEQ
            two == "!=" -> AidlTypes.NEQ
            two == "<=" -> AidlTypes.LTE
            two == ">=" -> AidlTypes.GTE
            else -> singleCharacterToken(buffer[tokenStart])
        }

        if (type != null) {
            tokenEnd = tokenStart + when (type) {
                AidlTypes.SPREAD -> 3
                AidlTypes.ARROW, AidlTypes.RANGE, AidlTypes.EQEQ, AidlTypes.NEQ, AidlTypes.LTE, AidlTypes.GTE -> 2
                else -> 1
            }
            tokenType = type
            when (type) {
                AidlTypes.LBRACE -> braceDepth++
                AidlTypes.RBRACE -> if (braceDepth > 0) braceDepth--
            }
        } else {
            tokenEnd = tokenStart + 1
            tokenType = TokenType.BAD_CHARACTER
        }
    }

    private fun scanWhile(type: IElementType, predicate: (Char) -> Boolean) {
        var index = tokenStart + 1
        while (index < endOffset && predicate(buffer[index])) {
            index++
        }
        tokenEnd = index
        tokenType = type
    }

    private fun isRegexStart(): Boolean {
        if (startsWith("//") || startsWith("/*")) {
            return false
        }
        val previous = previousSignificantChar()
        if (previous == null) {
            return true
        }
        return previous in "([{:=,!<>+-*%"
    }

    private fun previousSignificantChar(): Char? {
        var index = tokenStart - 1
        while (index >= startOffset && (buffer[index] == ' ' || buffer[index] == '\t' || buffer[index] == '\u000c')) {
            index--
        }
        return if (index < startOffset) null else buffer[index]
    }

    private fun isDeclarationKeywordPosition(): Boolean =
        braceDepth == 0 && (isAtLogicalLineStart() || previousWord() == "export")

    private fun isAtLogicalLineStart(): Boolean {
        var index = tokenStart - 1
        while (index >= startOffset) {
            val c = buffer[index]
            if (c == '\r' || c == '\n') {
                return true
            }
            if (c != ' ' && c != '\t' && c != '\u000c') {
                return false
            }
            index--
        }
        return true
    }

    private fun previousWord(): String? {
        var index = tokenStart - 1
        while (index >= startOffset && (buffer[index] == ' ' || buffer[index] == '\t' || buffer[index] == '\u000c')) {
            index--
        }
        val end = index + 1
        while (index >= startOffset && isIdentifierPart(buffer[index])) {
            index--
        }
        return if (end > index + 1) buffer.subSequence(index + 1, end).toString() else null
    }

    private fun startsWith(text: String, at: Int = tokenStart): Boolean {
        if (at + text.length > endOffset) {
            return false
        }
        for (offset in text.indices) {
            if (buffer[at + offset] != text[offset]) {
                return false
            }
        }
        return true
    }

    private fun singleCharacterToken(c: Char): IElementType? = when (c) {
        '(' -> AidlTypes.LPAREN
        ')' -> AidlTypes.RPAREN
        '{' -> AidlTypes.LBRACE
        '}' -> AidlTypes.RBRACE
        '[' -> AidlTypes.LBRACKET
        ']' -> AidlTypes.RBRACKET
        '<' -> AidlTypes.LT
        '>' -> AidlTypes.GT
        ',' -> AidlTypes.COMMA
        ':' -> AidlTypes.COLON
        '.' -> AidlTypes.DOT
        '?' -> AidlTypes.QUESTION
        '@' -> AidlTypes.AT
        '=' -> AidlTypes.EQ
        '+' -> AidlTypes.PLUS
        '-' -> AidlTypes.MINUS
        '*' -> AidlTypes.STAR
        '/' -> AidlTypes.SLASH
        '%' -> AidlTypes.PERCENT
        '&' -> AidlTypes.AMP
        else -> null
    }

    companion object {
        private const val BLOCK_COMMENT_FLAG = 1
        private const val BRACE_DEPTH_SHIFT = 1

        private fun isIdentifierStart(c: Char) = c == '_' || c in 'A'..'Z' || c in 'a'..'z'

        private fun isIdentifierPart(c: Char) = isIdentifierStart(c) || c.isDigit()
    }
}

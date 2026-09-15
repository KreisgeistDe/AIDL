package de.kreisgeist.aidl.compiler.frontend

class SourceProjectionException(
    val diagnostic: String,
    val offset: Int,
) : IllegalArgumentException("$diagnostic at offset $offset")

data class ProjectedDeclaration(
    val kind: String,
    val name: String,
    val exported: Boolean,
    val bodyTokens: List<String>,
    val offset: Int = -1,
    val endOffset: Int = -1,
    val nameOffset: Int = -1,
)

data class SourceProjection(
    val module: String?,
    val imports: List<String>,
    val declarations: List<ProjectedDeclaration>,
    val sourceId: String = "inline",
    val path: String = "inline.aidl",
) {
    fun stableSignature(): String = buildString {
        append("module=").append(module ?: "")
        append("\nimports=").append(imports.joinToString(","))
        append("\ndeclarations=")
        append(declarations.joinToString(",") { "${it.kind}:${it.name}:${it.exported}" })
    }
}

data class ProjectedReferenceToken(
    val reference: String,
    val terminal: String,
    val offset: Int,
    val length: Int,
)

private data class Token(val kind: Kind, val value: String, val offset: Int) {
    enum class Kind { WORD, STRING, NUMBER, SYMBOL, NEWLINE, EOF }
}

/**
 * First bounded M10.5-03 front-end slice.
 *
 * The projector deliberately owns only module/import headers and named enum/value/entity
 * declaration boundaries. Declaration bodies are retained as deterministic lexical tokens;
 * their semantics remain Python-owned. Any top-level form outside this bounded slice fails
 * closed rather than being silently accepted as Kotlin support.
 */
object AidlSourceProjector {
    private val supportedDeclarations = setOf("enum", "value", "entity")
    private val twoCharSymbols = setOf("->", "==", "!=", "<=", ">=", "..")
    private val singleSymbols = "{}[]()<>,:.*+-/%=?".toSet()

    fun project(source: String): SourceProjection = project("inline", "inline.aidl", source)

    fun project(sourceId: String, path: String, source: String): SourceProjection {
        val tokens = lex(source)
        var index = 0
        var module: String? = null
        val imports = mutableListOf<String>()
        val declarations = mutableListOf<ProjectedDeclaration>()

        fun current(): Token = tokens[index]
        fun advance(): Token = tokens[index++]
        fun skipNewlines() { while (current().kind == Token.Kind.NEWLINE) advance() }
        fun fail(message: String): Nothing = throw SourceProjectionException(message, current().offset)
        fun consumeWord(message: String): String {
            if (current().kind != Token.Kind.WORD) fail(message)
            return advance().value
        }
        fun lineEnd() {
            if (current().kind == Token.Kind.NEWLINE) {
                skipNewlines()
            } else if (current().kind != Token.Kind.EOF) {
                fail("expected end of line")
            }
        }
        fun qualifiedName(allowWildcard: Boolean): String {
            val parts = mutableListOf(consumeWord("expected qualified name"))
            while (current().value == ".") {
                advance()
                if (allowWildcard && current().value == "*") {
                    advance()
                    parts += "*"
                    break
                }
                parts += consumeWord("expected qualified name segment")
            }
            return parts.joinToString(".")
        }

        skipNewlines()
        while (current().kind != Token.Kind.EOF) {
            when (current().value) {
                "module" -> {
                    if (module != null || declarations.isNotEmpty()) fail("module must precede declarations")
                    advance()
                    module = qualifiedName(false)
                    lineEnd()
                }
                "import" -> {
                    if (declarations.isNotEmpty()) fail("import must precede declarations")
                    advance()
                    imports += qualifiedName(true)
                    lineEnd()
                }
                else -> {
                    var exported = false
                    if (current().value == "export") {
                        exported = true
                        advance()
                    }
                    val declarationOffset = current().offset
                    val kind = consumeWord("expected declaration kind")
                    if (kind !in supportedDeclarations) fail("unsupported declaration kind '$kind'")
                    val nameOffset = current().offset
                    val name = consumeWord("expected declaration name")
                    if (current().value != "{") fail("expected '{' after $kind $name")
                    advance()
                    var depth = 1
                    var declarationEndOffset = declarationOffset
                    val body = mutableListOf<String>()
                    while (depth > 0) {
                        val token = current()
                        if (token.kind == Token.Kind.EOF) fail("unterminated $kind $name body")
                        advance()
                        when (token.value) {
                            "{" -> { depth += 1; body += token.value }
                            "}" -> {
                                depth -= 1
                                if (depth > 0) {
                                    body += token.value
                                } else {
                                    declarationEndOffset = token.offset + token.value.length
                                }
                            }
                            else -> if (token.kind != Token.Kind.NEWLINE) body += token.value
                        }
                    }
                    declarations += ProjectedDeclaration(
                        kind,
                        name,
                        exported,
                        body,
                        declarationOffset,
                        declarationEndOffset,
                        nameOffset,
                    )
                    skipNewlines()
                }
            }
        }
        return SourceProjection(
            module = module,
            imports = imports.toList(),
            declarations = declarations.toList(),
            sourceId = sourceId,
            path = path,
        )
    }

    fun referenceAt(source: String, offset: Int): String? {
        if (offset < 0 || offset >= source.length) return null
        val tokens = lex(source)
        val index = tokens.indexOfFirst { token ->
            token.kind == Token.Kind.WORD &&
                token.offset <= offset &&
                offset < token.offset + token.value.length
        }
        if (index < 0) return null

        var start = index
        while (
            start >= 2 &&
            tokens[start - 1].kind == Token.Kind.SYMBOL &&
            tokens[start - 1].value == "." &&
            tokens[start - 2].kind == Token.Kind.WORD
        ) {
            start -= 2
        }
        var end = index
        while (
            end + 2 < tokens.size &&
            tokens[end + 1].kind == Token.Kind.SYMBOL &&
            tokens[end + 1].value == "." &&
            tokens[end + 2].kind == Token.Kind.WORD
        ) {
            end += 2
        }
        return tokens.subList(start, end + 1).joinToString("") { it.value }
    }

    /** Return terminal name tokens with the qualified reference they belong to. */
    fun terminalReferences(source: String): List<ProjectedReferenceToken> {
        val tokens = lex(source)
        return buildList {
            for (index in tokens.indices) {
                val terminal = tokens[index]
                if (terminal.kind != Token.Kind.WORD) continue
                if (
                    index + 2 < tokens.size &&
                    tokens[index + 1].kind == Token.Kind.SYMBOL &&
                    tokens[index + 1].value == "." &&
                    tokens[index + 2].kind == Token.Kind.WORD
                ) continue
                var start = index
                while (
                    start >= 2 &&
                    tokens[start - 1].kind == Token.Kind.SYMBOL &&
                    tokens[start - 1].value == "." &&
                    tokens[start - 2].kind == Token.Kind.WORD
                ) start -= 2
                add(
                    ProjectedReferenceToken(
                        reference = tokens.subList(start, index + 1).joinToString("") { it.value },
                        terminal = terminal.value,
                        offset = terminal.offset,
                        length = terminal.value.length,
                    )
                )
            }
        }
    }

    private fun lex(source: String): List<Token> {
        val result = mutableListOf<Token>()
        var index = 0
        fun add(kind: Token.Kind, value: String, offset: Int) { result += Token(kind, value, offset) }
        while (index < source.length) {
            val start = index
            val ch = source[index]
            val next = source.getOrNull(index + 1)
            when {
                ch == ' ' || ch == '\t' || ch == '\r' -> index += 1
                ch == '\n' -> { add(Token.Kind.NEWLINE, "\n", start); index += 1 }
                ch == '/' && next == '/' -> {
                    index += 2
                    while (index < source.length && source[index] != '\n') index += 1
                }
                ch == '/' && next == '*' -> {
                    val close = source.indexOf("*/", index + 2)
                    if (close < 0) throw SourceProjectionException("unterminated block comment", start)
                    index = close + 2
                }
                ch == '"' -> {
                    index += 1
                    var escaped = false
                    while (index < source.length) {
                        val current = source[index]
                        if (current == '\n') throw SourceProjectionException("newline in string literal", start)
                        index += 1
                        if (!escaped && current == '"') break
                        escaped = !escaped && current == '\\'
                        if (current != '\\') escaped = false
                    }
                    if (source.getOrNull(index - 1) != '"') throw SourceProjectionException("unterminated string literal", start)
                    add(Token.Kind.STRING, source.substring(start, index), start)
                }
                ch == '@' -> {
                    index += 1
                    while (index < source.length && source[index].isWordPart()) index += 1
                    if (index == start + 1) throw SourceProjectionException("empty annotation", start)
                    add(Token.Kind.WORD, source.substring(start, index), start)
                }
                ch.isDigit() || (ch == '-' && next?.isDigit() == true) -> {
                    if (ch == '-') index += 1
                    while (index < source.length && source[index].isDigit()) index += 1
                    if (source.getOrNull(index) == '.' && source.getOrNull(index + 1)?.isDigit() == true) {
                        index += 1
                        while (index < source.length && source[index].isDigit()) index += 1
                    }
                    if (source.getOrNull(index) == '%') index += 1
                    while (index < source.length && source[index].isLetter()) index += 1
                    add(Token.Kind.NUMBER, source.substring(start, index), start)
                }
                ch.isWordStart() -> {
                    index += 1
                    while (index < source.length && source[index].isWordPart()) index += 1
                    add(Token.Kind.WORD, source.substring(start, index), start)
                }
                index + 1 < source.length && source.substring(index, index + 2) in twoCharSymbols -> {
                    add(Token.Kind.SYMBOL, source.substring(index, index + 2), start)
                    index += 2
                }
                ch in singleSymbols -> { add(Token.Kind.SYMBOL, ch.toString(), start); index += 1 }
                else -> throw SourceProjectionException("unexpected character '$ch'", start)
            }
        }
        result += Token(Token.Kind.EOF, "", source.length)
        return result
    }

    private fun Char.isWordStart(): Boolean = this == '_' || isLetter()
    private fun Char.isWordPart(): Boolean = isWordStart() || isDigit()
}

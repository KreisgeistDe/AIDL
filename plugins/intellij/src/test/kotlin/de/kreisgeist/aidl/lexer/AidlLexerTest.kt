package de.kreisgeist.aidl.lexer

import com.intellij.psi.TokenType
import de.kreisgeist.aidl.psi.AidlTypes
import kotlin.test.Test
import kotlin.test.assertEquals

class AidlLexerTest {
    @Test
    fun `qualified import segments are identifiers and type names`() {
        val tokens = lex("import videohub.ui.app.VideoHubWeb\n")

        assertEquals(AidlTypes.IMPORT_KEYWORD, tokens[0].type)
        assertEquals("videohub", tokens[1].text)
        assertEquals(AidlTypes.IDENTIFIER, tokens[1].type)
        assertEquals("app", tokens[5].text)
        assertEquals(AidlTypes.IDENTIFIER, tokens[5].type)
        assertEquals("VideoHubWeb", tokens[7].text)
        assertEquals(AidlTypes.TYPE_NAME, tokens[7].type)
    }

    @Test
    fun `module and import path segments stay identifiers even when they are property names`() {
        val tokens = lex(
            """
            module calendar.system.api
            import calendar.operations.calendar.listMyEvents
            """.trimIndent(),
        )

        assertEquals(AidlTypes.MODULE_KEYWORD, tokens[0].type)
        assertEquals(AidlTypes.IDENTIFIER, tokens.single { it.text == "system" }.type)
        assertEquals(AidlTypes.IDENTIFIER, tokens.single { it.text == "api" }.type)
        assertEquals(AidlTypes.IMPORT_KEYWORD, tokens.single { it.text == "import" }.type)
        assertEquals(AidlTypes.IDENTIFIER, tokens.last { it.text == "calendar" }.type)
        assertEquals(AidlTypes.IDENTIFIER, tokens.single { it.text == "operations" }.type)
        assertEquals(AidlTypes.IDENTIFIER, tokens.single { it.text == "listMyEvents" }.type)
    }

    @Test
    fun `app clauses and profile version are property names`() {
        val tokens = lex(
            """
            app OfflineCalendar {
              profile core version 1
            }
            """.trimIndent(),
        )

        assertEquals(AidlTypes.APP_KEYWORD, tokens.single { it.text == "app" }.type)
        assertEquals(AidlTypes.PROPERTY_NAME, tokens.single { it.text == "profile" }.type)
        assertEquals(AidlTypes.PROPERTY_NAME, tokens.single { it.text == "version" }.type)
    }

    @Test
    fun `api block clauses are property names`() {
        val tokens = lex(
            """
            export api CalendarApi version 1 {
              transport rest
              auth inherit
            }
            """.trimIndent(),
        )

        assertEquals(AidlTypes.API_KEYWORD, tokens.single { it.text == "api" }.type)
        assertEquals(AidlTypes.VERSION_KEYWORD, tokens.single { it.text == "version" }.type)
        assertEquals(AidlTypes.PROPERTY_NAME, tokens.single { it.text == "transport" }.type)
        assertEquals(AidlTypes.PROPERTY_NAME, tokens.single { it.text == "auth" }.type)
    }

    @Test
    fun `quoted grammar terminals are keywords outside qualified paths`() {
        val tokens = lex(
            """
            value Window {
              mode queuedCommands
              retry: exponential(max: 3)
              data events = query listMyEvents
              cache: public ttl 30s vary [ownerId]
              limit: int(scalar)
            }
            """.trimIndent(),
        )

        for (text in listOf("queuedCommands", "exponential", "max", "query", "public", "ttl", "vary", "scalar")) {
            val token = tokens.single { it.text == text }
            assertEquals(text, token.type.toString(), "Token $text")
        }
    }

    private fun lex(text: String): List<Token> {
        val lexer = AidlLexer()
        lexer.start(text)
        val tokens = mutableListOf<Token>()
        while (lexer.tokenType != null) {
            val type = lexer.tokenType!!
            if (type != TokenType.WHITE_SPACE && type != AidlTypes.NEWLINE) {
                tokens += Token(type, text.substring(lexer.tokenStart, lexer.tokenEnd))
            }
            lexer.advance()
        }
        return tokens
    }

    private data class Token(
        val type: Any,
        val text: String,
    )
}

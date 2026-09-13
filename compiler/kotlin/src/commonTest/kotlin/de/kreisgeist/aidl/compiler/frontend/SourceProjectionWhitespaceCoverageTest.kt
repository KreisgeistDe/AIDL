package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class SourceProjectionWhitespaceCoverageTest {
    @Test
    fun coversTabsCarriageReturnsAndDigitWordSuffixes() {
        val projection = AidlSourceProjector.project(
            "module\tparity2\r\nvalue V2\t{ field2:\tstring\r required }\n",
        )
        assertEquals("parity2", projection.module)
        assertEquals("V2", projection.declarations.single().name)
        assertTrue(projection.declarations.single().bodyTokens.contains("field2"))
    }

    @Test
    fun coversSingleCharacterSymbolsAtEndOfLexicalDecisions() {
        val body = AidlSourceProjector.project("value V { x: string? y: [int] z: (int) }")
            .declarations.single().bodyTokens
        assertTrue(body.contains("?"))
        assertTrue(body.contains("["))
        assertTrue(body.contains("]"))
        assertTrue(body.contains("("))
        assertTrue(body.contains(")"))
    }
}

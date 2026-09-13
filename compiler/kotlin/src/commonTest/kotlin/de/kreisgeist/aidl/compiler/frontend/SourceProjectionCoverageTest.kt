package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class SourceProjectionCoverageTest {
    @Test
    fun coversRemainingLexicalBranches() {
        val projection = AidlSourceProjector.project(
            """
                // line comment
                module _m
                import only
                value V {
                  pct: decimal default 50%
                  range: int default 1..2
                  cmp: bool default 1<=2
                  arrow: string default a->b
                  minus: int default a-b
                  slash: int default a/b
                  escaped: string default "a\\\\b"
                }
            """.trimIndent(),
        )
        assertEquals("_m", projection.module)
        assertEquals(listOf("only"), projection.imports)
        assertFalse(projection.declarations.single().exported)
        val body = projection.declarations.single().bodyTokens
        assertTrue(body.contains("50%"))
        assertTrue(body.contains(".."))
        assertTrue(body.contains("<="))
        assertTrue(body.contains("->"))
        assertTrue(body.contains("-"))
        assertTrue(body.contains("/"))
        assertTrue(body.contains("\"a\\\\b\""))
    }

    @Test
    fun coversEofCommentImportAndDuplicateModuleRejections() {
        assertEquals(
            "module=\nimports=one\ndeclarations=",
            AidlSourceProjector.project("import one").stableSignature(),
        )
        assertEquals(
            "module=\nimports=\ndeclarations=",
            AidlSourceProjector.project("// comment without newline").stableSignature(),
        )
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("module one\nmodule two\n")
        }
    }

    @Test
    fun coversOtherTwoCharacterSymbolsAndNumericForms() {
        val body = AidlSourceProjector.project(
            "value V { a: bool default 1==1 b: bool default 1!=2 c: bool default 1>=0 d: int default -1.5ms }",
        ).declarations.single().bodyTokens
        assertTrue(body.contains("=="))
        assertTrue(body.contains("!="))
        assertTrue(body.contains(">="))
        assertTrue(body.contains("-1.5ms"))
    }
}

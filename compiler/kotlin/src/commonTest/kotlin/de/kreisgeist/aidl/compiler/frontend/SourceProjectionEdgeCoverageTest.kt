package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class SourceProjectionEdgeCoverageTest {
    @Test
    fun coversEmptyBodyAndTopLevelNameFailures() {
        val projection = AidlSourceProjector.project("value Empty {}")
        assertEquals(emptyList(), projection.declarations.single().bodyTokens)
        assertFailsWith<SourceProjectionException> { AidlSourceProjector.project("123") }
        assertFailsWith<SourceProjectionException> { AidlSourceProjector.project("export") }
    }

    @Test
    fun coversQualifiedNameWildcardBoundary() {
        assertFailsWith<SourceProjectionException> { AidlSourceProjector.project("module bad.*\n") }
        assertFailsWith<SourceProjectionException> { AidlSourceProjector.project("import bad.\n") }
    }

    @Test
    fun coversTerminalSymbolsAndEscapedStringFailures() {
        assertFailsWith<SourceProjectionException> { AidlSourceProjector.project("{") }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("value V { text: string default \"ends with slash \\")
        }
    }

    @Test
    fun coversAllSupportedDeclarationKindsWithoutExport() {
        val projection = AidlSourceProjector.project(
            "enum E {}\nvalue V {}\nentity N {}\n",
        )
        assertEquals(listOf("enum", "value", "entity"), projection.declarations.map { it.kind })
        assertTrue(projection.declarations.none { it.exported })
    }
}

package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals

class SourceProjectionFixtureTest {
    @Test
    fun sharedOracleFixturesMatchPinnedSignatures() {
        for (name in listOf("canonical-data", "legacy-data")) {
            val source = File("parity/$name.source").readText()
            val expected = File("parity/$name.signature").readText().trimEnd()
            assertEquals(expected, AidlSourceProjector.project(source).stableSignature(), name)
        }
    }
}

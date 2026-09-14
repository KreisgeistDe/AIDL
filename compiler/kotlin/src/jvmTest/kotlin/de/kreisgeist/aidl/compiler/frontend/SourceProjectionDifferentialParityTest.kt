package de.kreisgeist.aidl.compiler.frontend

import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.fail

class SourceProjectionDifferentialParityTest {
    private data class Case(
        val name: String,
        val filename: String,
        val expectedAccepted: Boolean,
    )

    private val cases = listOf(
        Case("positive", "source-projection-positive.source", true),
        Case("unexpected-character", "source-projection-unexpected-character.source", false),
        Case("unterminated-comment", "source-projection-unterminated-comment.source", false),
        Case("newline-string", "source-projection-newline-string.source", false),
    )

    private fun parityRoot(): Path {
        val local = Path.of("parity")
        if (Files.isDirectory(local)) return local
        val repositoryRelative = Path.of("compiler", "kotlin", "parity")
        if (Files.isDirectory(repositoryRelative)) return repositoryRelative
        fail("cannot locate compiler/kotlin/parity")
    }

    private fun caseSignature(root: Path, case: Case): String {
        val source = Files.readString(root.resolve(case.filename))
        val sourceId = case.filename.removeSuffix(".source")
        val path = "parity/${case.filename}"
        val prefix = "${case.name}|sourceId=$sourceId|path=$path"

        return try {
            val projection = AidlSourceProjector.project(sourceId, path, source)
            if (!case.expectedAccepted) fail("${case.filename} unexpectedly projected")
            assertEquals(sourceId, projection.sourceId)
            assertEquals(path, projection.path)
            val declarations = projection.declarations.joinToString(",") {
                "${it.kind}:${it.name}:${it.exported}@${it.offset}"
            }
            "$prefix|accepted=true|module=${projection.module.orEmpty()}|" +
                "imports=${projection.imports.joinToString(",")}|declarations=$declarations"
        } catch (error: SourceProjectionException) {
            if (case.expectedAccepted) throw error
            "$prefix|accepted=false|diagnostic=${error.diagnostic}@${error.offset}"
        }
    }

    private fun kotlinSignature(): String {
        val root = parityRoot()
        return cases.joinToString("\n") { caseSignature(root, it) }
    }

    @Test
    fun matchesPinnedRealPythonSourceProjectionSignature() {
        val root = parityRoot()
        val expected = Files.readString(root.resolve("source-projection.signature")).trimEnd()
        assertEquals(expected, kotlinSignature())
    }

    @Test
    fun repeatedProjectionIsDeterministic() {
        assertEquals(kotlinSignature(), kotlinSignature())
    }
}

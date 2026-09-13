package de.kreisgeist.aidl.compiler.frontend

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals

class NameResolutionFixtureTest {
    @Test
    fun sharedResolverFixtureMatchesPinnedPythonOracleSignature() {
        val sourceIds = listOf("resolution-consumer", "resolution-provider-a", "resolution-provider-b")
        val project = ProjectNameResolver.fromSources(
            sourceIds.map { sourceId -> sourceId to File("parity/$sourceId.source").readText() },
        )
        val queries = listOf("Local", "Public", "Hidden", "demo.shared.Hidden", "Duplicate", "Missing")
        val actual = buildString {
            append("symbols=")
            append(project.symbols.mapNotNull { it.stableIdentity }.joinToString(","))
            append("\nimports=")
            append(
                project.importResolutions.joinToString(";") { resolution ->
                    "${resolution.sourceId}|${resolution.importName}|" +
                        resolution.symbols.mapNotNull { it.stableIdentity }.joinToString(",")
                },
            )
            append("\nqueries=")
            append(
                queries.joinToString(";") { reference ->
                    val resolution = project.resolve("resolution-consumer", reference)
                    "$reference|${resolution.status.name}|" +
                        resolution.symbols.mapNotNull { it.stableIdentity }.joinToString(",")
                },
            )
        }
        assertEquals(File("parity/resolution.signature").readText().trimEnd(), actual)
    }
}

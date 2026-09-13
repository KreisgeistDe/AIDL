package de.kreisgeist.aidl.compiler.contract

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class ParityContractTest {
    private val digest = "sha256:" + "a".repeat(64)

    @Test
    fun exactRunnerInputsAndAuthoritiesAreStable() {
        assertEquals(listOf("source", "config", "profile"), ParityContract.runnerInputs)
        assertEquals("python", ParityContract.referenceImplementation)
        assertEquals(6, ParityContract.normativeBindings.size)
        assertTrue(ParityContract.semanticAllowlists.isEmpty())
    }

    @Test
    fun exactInputIdentityPassesAndPreservesRunnerOrder() {
        val value = mapOf("profile" to digest, "source" to digest, "config" to digest)
        val validated = ParityContract.validateInputIdentity(value)
        assertEquals(listOf("source", "config", "profile"), validated.keys.toList())
        assertEquals(value, validated)
    }

    @Test
    fun missingAndExtraInputKeysFailClosed() {
        assertFailsWith<IllegalArgumentException> {
            ParityContract.validateInputIdentity(mapOf("source" to digest, "config" to digest))
        }
        assertFailsWith<IllegalArgumentException> {
            ParityContract.validateInputIdentity(
                mapOf("source" to digest, "config" to digest, "profile" to digest, "workspace" to digest),
            )
        }
    }

    @Test
    fun malformedDigestsFailClosed() {
        val invalid = listOf(
            "sha256:" + "a".repeat(63),
            "sha512:" + "a".repeat(64),
            "sha256:" + "A".repeat(64),
            "sha256:" + "g".repeat(64),
        )
        invalid.forEach { bad ->
            assertFailsWith<IllegalArgumentException> {
                ParityContract.validateInputIdentity(
                    mapOf("source" to bad, "config" to digest, "profile" to digest),
                )
            }
        }
    }

    @Test
    fun deterministicJsonSortsKeysAndEscapesTransportText() {
        assertEquals(
            "{\"a\":\"line\\u000a\",\"b\":\"quote\\\"slash\\\\\"}",
            DeterministicJson.objectOf(mapOf("b" to "quote\"slash\\", "a" to "line\n")),
        )
    }

    @Test
    fun contractSnapshotIsDeterministicAndNonNormative() {
        val first = DeterministicJson.objectOf(ParityContract.contractSnapshot())
        val second = DeterministicJson.objectOf(ParityContract.contractSnapshot())
        assertEquals(first, second)
        assertTrue(first.contains("\"reference_implementation\":\"python\""))
        assertTrue(first.contains("\"semantic_allowlists\":\"0\""))
    }
}

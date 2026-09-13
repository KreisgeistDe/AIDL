package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class SourceProjectionTest {
    @Test
    fun projectsCanonicalDataSliceDeterministically() {
        val source = """
            module parity.canonical
            import parity.shared.Types
            import parity.shared.*

            export enum Status { active, archived }
            export value PetInput {
              name: string required
              note: string default "pet\\"name"
            }
            export entity Pet {
              field id: uuid primary
              field name: string required mutable
            }
        """.trimIndent()

        val first = AidlSourceProjector.project(source)
        val second = AidlSourceProjector.project(source)
        assertEquals(first, second)
        assertEquals("parity.canonical", first.module)
        assertEquals(listOf("parity.shared.Types", "parity.shared.*"), first.imports)
        assertEquals(
            "module=parity.canonical\nimports=parity.shared.Types,parity.shared.*\n" +
                "declarations=enum:Status:true,value:PetInput:true,entity:Pet:true",
            first.stableSignature(),
        )
        assertTrue(first.declarations[1].bodyTokens.contains("\"pet\\\"name\""))
    }

    @Test
    fun retainsLegacyEntityBodyAsLexicalSourceWithoutClaimingSemantics() {
        val projection = AidlSourceProjector.project(
            """
                module parity.legacy
                // Historical body spelling remains Python-owned.
                export entity Pet {
                  id: uuid primary
                  revision: revision generated concurrencyToken
                }
            """.trimIndent(),
        )
        assertEquals(
            listOf("id", ":", "uuid", "primary", "revision", ":", "revision", "generated", "concurrencyToken"),
            projection.declarations.single().bodyTokens,
        )
        assertEquals("module=parity.legacy\nimports=\ndeclarations=entity:Pet:true", projection.stableSignature())
    }

    @Test
    fun handlesCommentsNumbersNestedBodiesAndAnnotationsLexically() {
        val projection = AidlSourceProjector.project(
            """
                /* leading comment */
                module parity.tokens
                export value Example {
                  retries: int default -2
                  ttl: duration default 30s
                  ratio: decimal default 1.5
                  nested { @tag(value = "x") enabled: bool default true }
                }
            """.trimIndent(),
        )
        val body = projection.declarations.single().bodyTokens
        assertTrue(body.contains("-2"))
        assertTrue(body.contains("30s"))
        assertTrue(body.contains("1.5"))
        assertTrue(body.contains("@tag"))
        assertTrue(body.contains("{"))
        assertTrue(body.contains("}"))
    }

    @Test
    fun failsClosedForTopLevelFormsOutsideThisSlice() {
        val error = assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("module parity\nexport query findPets() -> [Pet]\n")
        }
        assertTrue(error.message.orEmpty().contains("unsupported declaration kind 'query'"))
    }

    @Test
    fun failsClosedForMalformedHeadersAndOrdering() {
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export enum Status extra { active }")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export enum { active }")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export enum Status { active }\nmodule late\n")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export enum Status { active }\nimport late.Name\n")
        }
    }

    @Test
    fun failsClosedForLexicalAndBalanceErrors() {
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export enum Status { active")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("/* unterminated")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export value V { x: string default \"unterminated }")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export value V { x: string default \"line\nvalue\" }")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export value V { @ x: string }")
        }
        assertFailsWith<SourceProjectionException> {
            AidlSourceProjector.project("export value V { x: string # }")
        }
    }

    @Test
    fun acceptsEmptyProgramAndEofTerminatedModule() {
        assertEquals("module=\nimports=\ndeclarations=", AidlSourceProjector.project("\n\n").stableSignature())
        assertEquals("module=single\nimports=\ndeclarations=", AidlSourceProjector.project("module single").stableSignature())
    }
}

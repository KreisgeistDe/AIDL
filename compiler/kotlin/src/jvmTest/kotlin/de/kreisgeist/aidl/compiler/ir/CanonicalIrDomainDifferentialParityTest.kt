package de.kreisgeist.aidl.compiler.ir

import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlin.test.fail

class CanonicalIrDomainDifferentialParityTest {
    private fun parityRoot(): Path {
        val local = Path.of("parity")
        if (Files.isDirectory(local)) return local
        val repositoryRelative = Path.of("compiler", "kotlin", "parity")
        if (Files.isDirectory(repositoryRelative)) return repositoryRelative
        fail("cannot locate compiler/kotlin/parity")
    }

    private fun positiveSignature(): String {
        val root = parityRoot()
        val filename = "canonical-ir-domain.source"
        val source = Files.readString(root.resolve(filename))
        val slice = CanonicalIrDomainSliceProjector.project(
            sourceId = "canonical-ir-domain",
            path = "compiler/kotlin/parity/$filename",
            source = source,
        )
        return "schema=valid\n${slice.stableSignature()}\nnegative|missing-module|rejected=true"
    }

    private fun reject(source: String): CanonicalIrDomainSliceException =
        assertFailsWith {
            CanonicalIrDomainSliceProjector.project("negative", "negative.aidl", source)
        }

    @Test
    fun matchesPinnedRealPythonCanonicalIrDomainSlice() {
        val root = parityRoot()
        val expected = Files.readString(root.resolve("canonical-ir-domain.signature")).trimEnd()
        assertEquals(expected, positiveSignature())
    }

    @Test
    fun repeatedCanonicalIrDomainProjectionIsDeterministic() {
        assertEquals(positiveSignature(), positiveSignature())
    }

    @Test
    fun missingModuleFailsClosed() {
        val source = Files.readString(parityRoot().resolve("canonical-ir-domain-missing-module.source"))
        val error = assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDomainSliceProjector.project(
                sourceId = "canonical-ir-domain-missing-module",
                path = "compiler/kotlin/parity/canonical-ir-domain-missing-module.source",
                source = source,
            )
        }
        assertTrue(error.message.orEmpty().contains("module"))
    }

    @Test
    fun boundedSliceCoversNullableLocalTypesAndFieldModifiers() {
        val source = """
            module parity.coverage

            export enum State { open, closed }
            export value Maybe {
              field state: State?
              names: [string]
            }
            export entity Item {
              id: uuid generated concurrencyToken
              state: State required sensitive
              name: string immutable onDelete none
            }
        """.trimIndent()
        val slice = CanonicalIrDomainSliceProjector.project("coverage", "coverage.aidl", source)
        assertEquals(listOf("enum", "value", "entity"), slice.declarations.map { it.kind })
        val maybe = slice.declarations[1]
        assertTrue(maybe.fields[0].type is CanonicalIrNullableType)
        assertFalse(maybe.fields[0].required)
        assertTrue(maybe.fields[1].type is CanonicalIrListType)
        val item = slice.declarations[2]
        assertEquals(listOf("id"), item.identityFields)
        assertTrue(item.fields[0].generated)
        assertTrue(item.fields[0].concurrencyToken)
        assertTrue(item.fields[1].sensitive)
        assertEquals("none", item.fields[2].onDelete)
    }

    @Test
    fun boundedSliceCoversAllOwnedOnDeleteValuesAndEmptyValueFields() {
        val source = """
            module parity.modifiers

            export value Empty {}
            export entity Item {
              id: uuid
              parent: Item? onDelete restrict
              child: Item? onDelete cascade
              detached: Item? onDelete setNull
            }
        """.trimIndent()
        val slice = CanonicalIrDomainSliceProjector.project("modifiers", "modifiers.aidl", source)
        assertTrue(slice.declarations[0].fields.isEmpty())
        val item = slice.declarations[1]
        assertEquals(listOf("id"), item.identityFields)
        assertEquals(listOf("none", "restrict", "cascade", "setNull"), item.fields.map { it.onDelete })
        assertTrue(item.fields.drop(1).all { !it.required })
    }

    @Test
    fun emptyDomainModuleProducesEmptyBoundedSlice() {
        val slice = CanonicalIrDomainSliceProjector.project(
            "empty",
            "empty.aidl",
            "module parity.empty\n",
        )
        assertTrue(slice.declarations.isEmpty())
        assertTrue(slice.sourceEntries.isEmpty())
        assertEquals("", slice.stableSignature())
    }

    @Test
    fun stableModelSignaturesCoverParameterizedAndNonDomainBranches() {
        val named = CanonicalIrNamedType(
            declarationId = "p.Box@1",
            fqn = "p.Box",
            typeArguments = listOf(CanonicalIrScalarType("string")),
        )
        assertEquals("named:p.Box@1:p.Box<scalar:string>", named.stableSignature())
        assertEquals("nullable<scalar:string>", CanonicalIrNullableType(CanonicalIrScalarType("string")).stableSignature())
        assertEquals("list<scalar:string>", CanonicalIrListType(CanonicalIrScalarType("string")).stableSignature())
        val other = CanonicalIrDomainDeclaration(
            kind = "other",
            declarationId = "p.Other@1",
            fqn = "p.Other",
            name = "Other",
            ownerModule = "p",
        )
        assertEquals("other|p.Other@1|p.Other|Other|p", other.stableSignature())
        assertEquals("", CanonicalIrDomainSlice(emptyList(), emptyList()).stableSignature())
    }

    @Test
    fun boundedSliceRejectsImportsDuplicatesAndMissingIdentity() {
        reject("module p\nimport q.Type\nexport value V { name: string }\n")
        reject("module p\nexport value V { name: string }\nexport value V { name: string }\n")
        reject("module p\nexport entity E { name: string }\n")
    }

    @Test
    fun boundedSliceRejectsNonOwnedDeclarationsAndTypeTargets() {
        reject("module p\napp A {}\n")
        val targetError = reject(
            "module p\napp A {}\nexport value V { other: A }\n",
        )
        assertTrue(targetError.message.orEmpty().contains("unsupported bounded type target"))
    }

    @Test
    fun boundedSliceRejectsMalformedEnums() {
        reject("module p\nexport enum E { one two }\n")
        reject("module p\nexport enum E { }\n")
        reject("module p\nexport enum E { , one }\n")
        reject("module p\nexport enum E { one, }\n")
    }

    @Test
    fun boundedSliceRejectsMalformedFields() {
        reject("module p\nexport value V { name string }\n")
        reject("module p\nexport value V { name: [string }\n")
        reject("module p\nexport value V { name: ] }\n")
        reject("module p\nexport value V { name: string required weird }\n")
        reject("module p\nexport value V { name: string onDelete }\n")
        reject("module p\nexport value V { name: string onDelete explode }\n")
        reject("module p\nexport value V { name: string default \"x\" }\n")
    }

    @Test
    fun boundedSliceRejectsUnsupportedTypes() {
        reject("module p\nexport value V { other: Missing }\n")
        reject("module p\nexport value V { other: map<string,string> }\n")
        reject("module p\nexport value V { other: string(1..80) }\n")
    }
}

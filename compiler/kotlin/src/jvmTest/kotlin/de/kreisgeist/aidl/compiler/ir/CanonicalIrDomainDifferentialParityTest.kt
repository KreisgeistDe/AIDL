package de.kreisgeist.aidl.compiler.ir

import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
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
              state: State?
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
        assertTrue(maybe.fields[1].type is CanonicalIrListType)
        val item = slice.declarations[2]
        assertEquals(listOf("id"), item.identityFields)
        assertTrue(item.fields[0].generated)
        assertTrue(item.fields[0].concurrencyToken)
        assertTrue(item.fields[1].sensitive)
        assertEquals("none", item.fields[2].onDelete)
    }

    @Test
    fun boundedSliceRejectsImportsDuplicatesAndMissingIdentity() {
        assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDomainSliceProjector.project(
                "imported",
                "imported.aidl",
                "module p\nimport q.Type\nexport value V { name: string }\n",
            )
        }
        assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDomainSliceProjector.project(
                "duplicate",
                "duplicate.aidl",
                "module p\nexport value V { name: string }\nexport value V { name: string }\n",
            )
        }
        assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDomainSliceProjector.project(
                "identity",
                "identity.aidl",
                "module p\nexport entity E { name: string }\n",
            )
        }
    }

    @Test
    fun boundedSliceRejectsMalformedEnumAndUnsupportedTypes() {
        assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDomainSliceProjector.project(
                "enum",
                "enum.aidl",
                "module p\nexport enum E { one two }\n",
            )
        }
        assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDomainSliceProjector.project(
                "unresolved",
                "unresolved.aidl",
                "module p\nexport value V { other: Missing }\n",
            )
        }
        assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDomainSliceProjector.project(
                "generic",
                "generic.aidl",
                "module p\nexport value V { other: map<string,string> }\n",
            )
        }
    }
}

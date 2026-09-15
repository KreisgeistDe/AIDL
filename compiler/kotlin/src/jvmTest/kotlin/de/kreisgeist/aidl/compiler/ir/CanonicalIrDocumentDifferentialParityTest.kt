package de.kreisgeist.aidl.compiler.ir

import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlin.test.fail

class CanonicalIrDocumentDifferentialParityTest {
    private fun parityRoot(): Path {
        val local = Path.of("parity")
        if (Files.isDirectory(local)) return local
        val repositoryRelative = Path.of("compiler", "kotlin", "parity")
        if (Files.isDirectory(repositoryRelative)) return repositoryRelative
        fail("cannot locate compiler/kotlin/parity")
    }

    private fun project(): CanonicalIrDocumentSlice {
        val root = parityRoot()
        val domainName = "canonical-ir-domain.source"
        val envelopeName = "canonical-ir-envelope.source"
        return CanonicalIrDocumentSliceProjector.project(
            domainSourceId = "canonical-ir-domain",
            domainPath = "compiler/kotlin/parity/$domainName",
            domainSource = Files.readString(root.resolve(domainName)),
            envelopeSourceId = "canonical-ir-envelope",
            envelopePath = "compiler/kotlin/parity/$envelopeName",
            envelopeSource = Files.readString(root.resolve(envelopeName)),
        )
    }

    @Test
    fun matchesPinnedRealPythonFullDocumentStructure() {
        val expected = Files.readString(parityRoot().resolve("canonical-ir-document.signature")).trimEnd()
        assertEquals(expected, project().structuralJson())
    }

    @Test
    fun completeDocumentIsDeterministicAndCarriesEveryRequiredRootField() {
        val first = project().canonicalJson()
        val second = project().canonicalJson()
        assertEquals(first, second)
        listOf(
            "\"irVersion\":\"0.3.0\"",
            "\"semanticHash\":\"sha256:",
            "\"profiles\":[",
            "\"app\":{",
            "\"declarations\":[",
            "\"system\":{",
            "\"deployments\":[",
            "\"sourceMap\":{",
            "\"profileExtensions\":{}",
        ).forEach { required -> assertTrue(first.contains(required), required) }
        assertFalse(project().structuralJson().contains("semanticHash"))
    }

    @Test
    fun boundedEnvelopeRejectsUnsupportedOrInconsistentFacts() {
        val root = parityRoot()
        val domain = Files.readString(root.resolve("canonical-ir-domain.source"))
        val envelope = Files.readString(root.resolve("canonical-ir-envelope.source"))

        fun reject(candidate: String): CanonicalIrDocumentSliceException = assertFailsWith {
            CanonicalIrDocumentSliceProjector.project(
                "domain",
                "compiler/kotlin/parity/canonical-ir-domain.source",
                domain,
                "envelope",
                "compiler/kotlin/parity/canonical-ir-envelope.source",
                candidate,
            )
        }

        assertTrue(reject(envelope.replace("import parity.ir.domain.*", "import other.domain.*")).message.orEmpty().contains("import"))
        assertTrue(reject(envelope.replace("uses []", "uses [SomeResource]")).message.orEmpty().contains("outside bounded"))
        assertTrue(reject(envelope.replace("resources []", "resources [SomeResource]")).message.orEmpty().contains("outside bounded"))
        assertTrue(reject(envelope + "\nexport query NotOwned {}\n").message.orEmpty().contains("unsupported"))
        assertTrue(reject(envelope.replace("system ParitySystem", "system OtherSystem")).message.orEmpty().contains("does not match"))
    }

    @Test
    fun existingDomainFailClosedBoundaryRemainsComposed() {
        val root = parityRoot()
        val invalidDomain = Files.readString(root.resolve("canonical-ir-domain-default.source"))
        val envelope = Files.readString(root.resolve("canonical-ir-envelope.source"))
        val error = assertFailsWith<CanonicalIrDomainSliceException> {
            CanonicalIrDocumentSliceProjector.project(
                "domain-default",
                "compiler/kotlin/parity/canonical-ir-domain-default.source",
                invalidDomain,
                "envelope",
                "compiler/kotlin/parity/canonical-ir-envelope.source",
                envelope,
            )
        }
        assertTrue(error.message.orEmpty().contains("default is not represented"))
    }
}

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
    fun boundedEnvelopeRejectsEveryUnsupportedShapeOrReference() {
        val root = parityRoot()
        val domain = Files.readString(root.resolve("canonical-ir-domain.source"))
        val envelope = Files.readString(root.resolve("canonical-ir-envelope.source"))

        fun reject(candidate: String) {
            assertFailsWith<CanonicalIrDocumentSliceException> {
                CanonicalIrDocumentSliceProjector.project(
                    "domain",
                    "compiler/kotlin/parity/canonical-ir-domain.source",
                    domain,
                    "envelope",
                    "compiler/kotlin/parity/canonical-ir-envelope.source",
                    candidate,
                )
            }
        }

        listOf(
            envelope.replace("import parity.ir.domain.*", "import other.domain.*"),
            envelope + "\nimport parity.ir.domain.*\n",
            envelope.replace("uses []", "uses [SomeResource]"),
            envelope.replace("exposes []", "exposes [SomeQuery]"),
            envelope.replace("runs []", "runs [SomeTask]"),
            envelope.replace("resources []", "resources [SomeResource]"),
            envelope.replace("apis []", "apis [SomeApi]"),
            envelope.replace("owns [parity.ir.domain.Pet]", "owns [parity.ir.domain.Missing]"),
            envelope.replace("services [ParityService]", "services [MissingService]"),
            envelope.replace("roles [user]", "roles user"),
            envelope.replace("roles [user]", "roles [user, ]"),
            envelope.replace("subject claim \"sub\"", "subject principal"),
            envelope.replace("serviceIdentities required", "serviceIdentities maybe"),
            envelope.replace("  profile core version 1\n", ""),
            envelope + "\nexport query NotOwned {}\n",
            envelope.replace("\n  system ParitySystem\n", "\n  system OtherSystem\n"),
            envelope.replace("defaultDeployment local", "defaultDeployment other"),
            envelope.replace("  colocate services all\n", ""),
            envelope.replace("  colocate services all\n", "  colocate services all\n  region nowhere\n"),
            envelope.replace("  provider oidc\n", ""),
            envelope.replace("  roles [user]\n", ""),
            envelope.replace("  scopes [parity.read]\n", ""),
            envelope.replace("  environment test\n", ""),
            envelope.replace("  target process\n", ""),
        ).forEach(::reject)

        val appBlock = """
            app ParityApp {
              profile core version 1
              system ParitySystem
              defaultDeployment local
            }
        """.trimIndent()
        val authBlock = """
            auth {
              provider oidc
              subject claim "sub"
              roles [user]
              scopes [parity.read]
              serviceIdentities required
            }
        """.trimIndent()
        val serviceBlock = """
            export service ParityService {
              owns [parity.ir.domain.Pet]
              uses []
              exposes []
              runs []
            }
        """.trimIndent()
        val systemBlock = """
            export system ParitySystem {
              services [ParityService]
              resources []
              apis []
            }
        """.trimIndent()
        val deploymentBlock = """
            export deployment local for ParitySystem {
              environment test
              target process
              colocate services all
            }
        """.trimIndent()

        listOf(
            envelope.replace(appBlock, ""),
            envelope.replace(appBlock, "$appBlock\n\n$appBlock"),
            envelope.replace(authBlock, ""),
            envelope.replace(authBlock, "$authBlock\n\n$authBlock"),
            envelope.replace(serviceBlock, ""),
            envelope.replace(serviceBlock, "$serviceBlock\n\n$serviceBlock"),
            envelope.replace(systemBlock, ""),
            envelope.replace(systemBlock, "$systemBlock\n\n$systemBlock"),
            envelope.replace(deploymentBlock, ""),
            envelope.replace(deploymentBlock, "$deploymentBlock\n\n$deploymentBlock"),
        ).forEach(::reject)
    }

    @Test
    fun boundedDocumentCoversNullableTypesAndDeterministicJsonScalarBranches() {
        val root = parityRoot()
        val domain = Files.readString(root.resolve("canonical-ir-domain.source"))
            .replace("status: Status required", "status: Status?", ignoreCase = false)
        val envelope = Files.readString(root.resolve("canonical-ir-envelope.source"))
        val nullable = CanonicalIrDocumentSliceProjector.project(
            "nullable-domain",
            "nullable-domain.aidl",
            domain,
            "envelope",
            "envelope.aidl",
            envelope,
        ).canonicalJson()
        assertTrue(nullable.contains("\"kind\":\"nullable\""))

        val encoded = CanonicalIrDocumentSlice(
            mapOf(
                "null" to null,
                "boolean" to true,
                "int" to 1,
                "long" to 2L,
                "double" to 3.5,
                "float" to 4.5f,
                "escaped" to "\b\u000C\n\r\t\"\\\u0001",
            ),
        ).canonicalJson()
        assertTrue(encoded.contains("\\b\\f\\n\\r\\t\\\"\\\\\\u0001"))
        assertFailsWith<CanonicalIrDocumentSliceException> {
            CanonicalIrDocumentSlice(mapOf("unsupported" to Any())).canonicalJson()
        }
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

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
        assertTrue(reject(envelope + "\nimport parity.ir.domain.*\n").message.orEmpty().contains("import"))
        assertTrue(reject(envelope.replace("uses []", "uses [SomeResource]")).message.orEmpty().contains("outside bounded"))
        assertTrue(reject(envelope.replace("exposes []", "exposes [SomeQuery]")).message.orEmpty().contains("outside bounded"))
        assertTrue(reject(envelope.replace("runs []", "runs [SomeTask]")).message.orEmpty().contains("outside bounded"))
        assertTrue(reject(envelope.replace("resources []", "resources [SomeResource]")).message.orEmpty().contains("outside bounded"))
        assertTrue(reject(envelope.replace("apis []", "apis [SomeApi]")).message.orEmpty().contains("outside bounded"))
        assertTrue(reject(envelope.replace("owns [parity.ir.domain.Pet]", "owns [parity.ir.domain.Missing]")).message.orEmpty().contains("unresolved"))
        assertTrue(reject(envelope.replace("services [ParityService]", "services [MissingService]")).message.orEmpty().contains("unresolved"))
        assertTrue(reject(envelope.replace("roles [user]", "roles user")).message.orEmpty().contains("bracketed"))
        assertTrue(reject(envelope.replace("roles [user]", "roles [user, ]")).message.orEmpty().contains("empty item"))
        assertTrue(reject(envelope.replace("subject claim \"sub\"", "subject principal")).message.orEmpty().contains("subject claim"))
        assertTrue(reject(envelope.replace("serviceIdentities required", "serviceIdentities maybe")).message.orEmpty().contains("serviceIdentities"))
        assertTrue(reject(envelope.replace("  profile core version 1\n", "")).message.orEmpty().contains("profile"))
        assertTrue(reject(envelope + "\nexport query NotOwned {}\n").message.orEmpty().contains("unsupported"))
        assertTrue(
            reject(
                envelope.replace(
                    "\n  system ParitySystem\n",
                    "\n  system OtherSystem\n",
                ),
            ).message.orEmpty().contains("does not match"),
        )
        assertTrue(reject(envelope.replace("defaultDeployment local", "defaultDeployment other")).message.orEmpty().contains("deployment references"))
        assertTrue(reject(envelope.replace("  colocate services all\n", "")).message.orEmpty().contains("colocate"))
        assertTrue(reject(envelope.replace("  colocate services all\n", "  colocate services all\n  region nowhere\n")).message.orEmpty().contains("unsupported deployment fact"))

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

        assertTrue(reject(envelope.replace(appBlock, "")).message.orEmpty().contains("exactly one app"))
        assertTrue(reject(envelope.replace(appBlock, "$appBlock\n\n$appBlock")).message.orEmpty().contains("exactly one app"))
        assertTrue(reject(envelope.replace(authBlock, "")).message.orEmpty().contains("exactly one auth"))
        assertTrue(reject(envelope.replace(authBlock, "$authBlock\n\n$authBlock")).message.orEmpty().contains("exactly one auth"))
        assertTrue(reject(envelope.replace(systemBlock, "")).message.orEmpty().contains("exactly one system"))
        assertTrue(reject(envelope.replace(systemBlock, "$systemBlock\n\n$systemBlock")).message.orEmpty().contains("exactly one system"))
        assertTrue(reject(envelope.replace(serviceBlock, "")).message.orEmpty().contains("at least one service"))
        assertTrue(reject(envelope.replace(serviceBlock, "$serviceBlock\n\n$serviceBlock")).message.orEmpty().contains("unique service"))
        assertTrue(reject(envelope.replace(deploymentBlock, "")).message.orEmpty().contains("exactly one deployment"))
        assertTrue(reject(envelope.replace(deploymentBlock, "$deploymentBlock\n\n$deploymentBlock")).message.orEmpty().contains("exactly one deployment"))

        assertTrue(reject(envelope.replace("  provider oidc\n", "")).message.orEmpty().contains("provider"))
        assertTrue(reject(envelope.replace("  roles [user]\n", "")).message.orEmpty().contains("roles"))
        assertTrue(reject(envelope.replace("  scopes [parity.read]\n", "")).message.orEmpty().contains("scopes"))
        assertTrue(reject(envelope.replace("  environment test\n", "")).message.orEmpty().contains("environment"))
        assertTrue(reject(envelope.replace("  target process\n", "")).message.orEmpty().contains("target"))
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

package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class MaterializationRecursionParityTest {
    private val consumerSource = """
        module demo.consumer
        import demo.shared.*
        value RecursiveValue {
          field accepted: [[PublicEntity?]?]?
          field recursive: [RecursiveValue?]?
          field unsupported: [[myQuery?]?]?
          field missing: [Missing?]?
          field ambiguous: [Duplicate?]?
        }
    """.trimIndent() + "\n"

    private fun resolver(): ProjectNameResolver {
        val consumer = ProjectedDocument(
            "consumer.aidl",
            AidlSourceProjector.project(consumerSource),
        )
        val providerAProjection = AidlSourceProjector.project(
            """
                module demo.shared
                export entity PublicEntity {}
                export entity Duplicate {}
            """.trimIndent(),
        )
        val providerA = ProjectedDocument(
            "provider-a.aidl",
            providerAProjection.copy(
                declarations = providerAProjection.declarations +
                    ProjectedDeclaration("query", "myQuery", true, emptyList()),
            ),
        )
        val providerB = ProjectedDocument(
            "provider-b.aidl",
            AidlSourceProjector.project(
                """
                    module demo.shared
                    export entity Duplicate {}
                """.trimIndent(),
            ),
        )
        return ProjectNameResolver.fromProjectedDocuments(listOf(consumer, providerA, providerB))
    }

    private fun checks(): List<ProjectedFieldMaterializationCheck> {
        val projection = AidlSourceProjector.project(consumerSource)
        return ProjectedMaterializationChecker.checkProjectedFields(
            sourceId = "consumer.aidl",
            declaration = projection.declarations.single(),
            resolver = resolver(),
        )
    }

    private fun render(field: ProjectedFieldMaterializationCheck): String {
        val location = field.check.location
        return listOf(
            field.fieldName,
            field.typeSource,
            field.check.status.toString(),
            field.check.diagnosticCode.orEmpty(),
            field.check.sourcePath.orEmpty(),
            location?.line?.toString().orEmpty(),
            location?.column?.toString().orEmpty(),
            location?.offset?.toString().orEmpty(),
        ).joinToString("|")
    }

    private fun signature(): String = checks().joinToString("\n", transform = ::render)

    @Test
    fun nestedValueFieldMaterializationMatchesPinnedOrderingAndOwnership() {
        val expected = """
            accepted|[[PublicEntity?]?]?|MATERIALIZABLE|||||
            recursive|[RecursiveValue?]?|MATERIALIZABLE|||||
            unsupported|[[myQuery?]?]?|OUTSIDE_SLICE|||||
            missing|[Missing?]?|UNRESOLVED|AIDL-T001||||
            ambiguous|[Duplicate?]?|AMBIGUOUS|CORE-S023||||
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun recursiveTraversalPreservesResolverOwnershipAndLocationAbsence() {
        val byName = checks().associateBy { it.fieldName }
        assertEquals(ProjectedMaterializationStatus.MATERIALIZABLE, byName.getValue("accepted").check.status)
        assertEquals(ProjectedMaterializationStatus.MATERIALIZABLE, byName.getValue("recursive").check.status)
        assertEquals(ProjectedMaterializationStatus.OUTSIDE_SLICE, byName.getValue("unsupported").check.status)
        for (name in listOf("unsupported", "missing", "ambiguous")) {
            assertEquals(null, byName.getValue(name).check.sourcePath)
            assertEquals(null, byName.getValue(name).check.location)
        }
    }

    @Test
    fun entityTraversalAndMalformedProjectedFieldsFailClosed() {
        val entity = ProjectedDeclaration(
            "entity",
            "Holder",
            false,
            listOf("noise", "field", "accepted", ":", "PublicEntity"),
        )
        val result = ProjectedMaterializationChecker.checkProjectedFields(
            sourceId = "consumer.aidl",
            declaration = entity,
            resolver = resolver(),
        )
        assertEquals(ProjectedMaterializationStatus.MATERIALIZABLE, result.single().check.status)

        assertFailsWith<IllegalArgumentException> {
            ProjectedMaterializationChecker.checkProjectedFields(
                sourceId = "consumer.aidl",
                declaration = ProjectedDeclaration("value", "Broken", false, listOf("field", "broken", ":")),
                resolver = resolver(),
            )
        }
    }

    @Test
    fun fieldTraversalIsBoundedToValueAndEntityDeclarations() {
        assertFailsWith<IllegalArgumentException> {
            ProjectedMaterializationChecker.checkProjectedFields(
                sourceId = "consumer.aidl",
                declaration = ProjectedDeclaration("enum", "NoFields", false, emptyList()),
                resolver = resolver(),
            )
        }
    }
}
